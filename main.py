"""
300英雄宅基地自动任务工具 - 主程序
"""
import sys
import time
from datetime import datetime
from typing import Optional
from logger import logger
from config_manager import Config
from api_client import APIClient
from services import (
    UserService, 
    PostService, 
    SocialService, 
    TaskService, 
    StatsService
)


def get_current_time() -> str:
    """获取当前时间字符串"""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


# 分享战绩的 TASK_ACTION action 值（用户实测确认）
SHARE_ACTION_RECORD = "record_share"    # 分享战绩（实测确认）
# 分享帖子=转发帖子（PUBLISH_POST + from_post），无需 TASK_ACTION


class TaskRunner:
    """任务执行器"""
    
    def __init__(self, account: 'AccountConfig', global_config: Config):
        """
        初始化任务执行器
        
        Args:
            account: 当前要执行的账号配置
            global_config: 全局配置对象（已加载，包含所有配置项）
        """
        self.config = global_config
        self.account = account
        
        # 设置当前账号的token到config中
        self.config._config['token'] = account.token
        
        self.client = APIClient(self.config)
        
        # 初始化服务
        self.user_service = UserService(self.client, self.config)
        self.post_service = PostService(self.client, self.config)
        self.social_service = SocialService(self.client, self.config)
        self.task_service = TaskService(self.client, self.config)
        self.stats_service = StatsService(self.client, self.config)
        
        # 用户信息
        self.unique_id = None
        self.account_id = None
        self.guid = None
        self.role_id = None
        self.role_name = None
    
    def authenticate(self) -> bool:
        """
        认证用户
        
        Returns:
            是否认证成功
        """
        logger.info(f"正在验证Token... [{self.account.name}]")
        
        msg_data = self.user_service.validate_token()
        
        if not msg_data:
            return False
        
        # 保存用户信息
        self.unique_id = msg_data["UniqueId"]
        self.account_id = msg_data["JumpwUID"]
        self.guid = msg_data["JumpwGuid"]
        self.role_id = int(msg_data["JumpwRoleId"])
        self.role_name = msg_data["JumpwRoleName"]
        
        logger.info(f"用户认证成功: {self.role_name} (ID: {self.role_id})")
        return True
    
    def execute_daily_tasks(self):
        """执行每日任务"""
        logger.info("=" * 50)
        logger.info("开始执行每日任务")
        logger.info("=" * 50)
        
        # 1. 查询战绩
        self._task_query_stats()
        
        # 2. 关注和取消关注
        self._task_follow_and_unfollow()
        
        # 3. 签到
        self._task_sign_in()
        
        # 4. 游玩共鸣引擎
        self._task_play_resonance_game()
        
        # 5. 清理残留任务帖（上次运行发帖超时未删除的）
        self._task_cleanup_stale_posts()
        
        # 6. 发帖（创建新帖子，后续所有帖子操作都针对此帖；失败自动确认重试）
        post_id = self._task_create_post()
        
        # 7. 帖子相关操作（浏览 → 点赞 → 收藏 → 评论 → 删除）
        if post_id:
            # 浏览帖子（带重试，成功后才继续点赞和评论）
            if self._task_view_post_with_retry(post_id):
                self._task_like(post_id)
                self._task_collect(post_id)
                self._task_comment(post_id)
            else:
                logger.warning("浏览帖子最终失败，跳过点赞和评论操作")
            # 删除帖子
            self._task_delete_post(post_id)
        
        # 8. 购买道具
        self._task_buy_item()
        
        # 9. 任务驱动补足（读取今日随机任务，按缺口补足动作次数）
        self._task_fulfill_daily_tasks()
        
        # 10. 领取所有奖励（统一放到任务最后）
        self._task_claim_monthly_rewards()      # 月度累计签到奖励
        self._task_claim_resonance_reward()     # 共鸣引擎奖励
        self._task_claim_rewards()              # 每日任务奖励
        
        # 11. 兜底清理本次运行残留的任务帖（删除超时未删掉的）
        self._task_cleanup_stale_posts()
        
        logger.info("=" * 50)
        logger.info("所有任务执行完毕")
        logger.info("=" * 50)
    
    def _is_task_post(self, post: dict) -> bool:
        """
        判断帖子是否为脚本生成的任务帖（标题+简介双重匹配，避免误删用户手动发的帖子）
        
        任务帖特征：标题以"这是一个任务帖子"开头，且简介固定为"这是一个任务帖子"
        """
        title = post.get("title") or ""
        brief = post.get("brief") or ""
        return title.startswith("这是一个任务帖子") and brief == "这是一个任务帖子"
    
    def _find_just_created_post(self) -> Optional[int]:
        """查询最近发布的匹配任务标题的帖子（发帖超时后确认是否已实际发布）"""
        my_posts = self.post_service.get_my_posts(self.unique_id)
        for post in my_posts:
            if self._is_task_post(post):
                return post["postid"]
        return None
    
    def _task_cleanup_stale_posts(self):
        """清理历史残留的任务帖（只删任务生成的帖子；发出删除请求即走，不动用户帖子）"""
        logger.info("\n[任务] 清理残留任务帖")
        my_posts = self.post_service.get_my_posts(self.unique_id)
        removed = 0
        for post in my_posts:
            if not self._is_task_post(post):
                continue
            self.post_service.delete_post(post["postid"])
            removed += 1
            time.sleep(self.config.request_delay)
        
        if removed > 0:
            logger.info(f"已发送 {removed} 个残留任务帖的删除请求")
        else:
            logger.info("无残留任务帖")
    
    def _task_create_post(self) -> Optional[int]:
        """任务: 发帖（失败自动确认重试，返回帖子ID供后续操作使用）"""
        logger.info("\n[任务] 发帖")
        title = f"这是一个任务帖子 - {get_current_time()}"
        brief = "这是一个任务帖子"
        content = "这是一个任务帖子"
        
        max_retries = self.config.max_retries
        retry_delay = self.config.retry_delay
        
        for attempt in range(1, max_retries + 1):
            post_id = self.post_service.create_post(
                self.unique_id,
                title,
                tabs_id=401,
                brief=brief,
                content=content
            )
            
            if post_id:
                logger.info(f"发帖成功，帖子ID: {post_id}，后续操作将针对此帖")
                time.sleep(self.config.request_delay)
                return post_id
            
            # 失败后先查询确认：请求超时但帖子可能已实际发布，避免重复发帖
            confirmed_id = self._find_just_created_post()
            if confirmed_id is not None:
                logger.info(
                    f"检测到帖子实际已发布成功 (帖子ID: {confirmed_id})，复用该帖子，不再重复发帖"
                )
                time.sleep(self.config.request_delay)
                return confirmed_id
            
            if attempt < max_retries:
                logger.warning(
                    f"发帖失败且未检测到已发布帖子，{retry_delay}秒后重试 ({attempt}/{max_retries})..."
                )
                time.sleep(retry_delay)
        
        logger.error(f"发帖失败，已重试 {max_retries} 次，跳过帖子相关操作")
        return None
    
    def _task_delete_post(self, post_id: int):
        """任务: 删除帖子（发出请求即走，不等待响应）"""
        logger.info("\n[任务] 删除帖子")
        self.post_service.delete_post(post_id)
        time.sleep(self.config.request_delay)
    
    def _task_like(self, post_id: int):
        """任务: 点赞帖子（每次都是新帖，无需取消点赞）"""
        logger.info("\n[任务] 点赞操作")
        
        self.post_service.like_post(self.unique_id, post_id, 1)
        time.sleep(self.config.request_delay)
    
    def _task_collect(self, post_id: int):
        """任务: 收藏帖子（每次都是新帖，无需取消收藏）"""
        logger.info("\n[任务] 收藏帖子")
        
        self.post_service.collect_post(self.unique_id, post_id, 1)
        time.sleep(self.config.request_delay)
    
    def _task_query_stats(self):
        """任务: 查询战绩"""
        logger.info("\n[任务] 查询战绩")
        
        self.stats_service.query_performance(
            self.account_id, 
            self.guid, 
            "", 
            self.role_id
        )
        time.sleep(self.config.request_delay)
        
        self.stats_service.query_history(
            self.role_id, 
            1, 
            1
        )
        time.sleep(self.config.request_delay)
    
    def _task_follow_and_unfollow(self):
        """任务: 关注和取消关注"""
        logger.info("\n[任务] 关注操作")
        follow_id = self.config.default_follow_id
        
        self.social_service.follow_user(self.unique_id, follow_id, 1)
        time.sleep(self.config.request_delay)
        
        self.social_service.follow_user(self.unique_id, follow_id, 2)
    
    def _task_sign_in(self):
        """任务: 签到"""
        logger.info("\n[任务] 签到")
        self.user_service.sign_in(self.unique_id)
        time.sleep(self.config.request_delay)
    
    def _task_claim_monthly_rewards(self):
        """任务: 领取月度累计签到奖励（3天/7天/15天/28天，一次批量领取）"""
        logger.info("\n[任务] 领取月度累计签到奖励")
        task_ids = self.config.monthly_signin_task_ids
        self.task_service.claim_rewards_batch(self.unique_id, task_ids)
    
    def _task_play_resonance_game(self):
        """任务: 游玩共鸣引擎（奖励在最后统一领取）"""
        logger.info("\n[任务] 游玩共鸣引擎")
        self.user_service.play_resonance_game()
        time.sleep(self.config.request_delay)
    
    def _task_claim_resonance_reward(self):
        """任务: 领取共鸣引擎任务奖励"""
        logger.info("\n[任务] 领取共鸣引擎任务奖励")
        self.task_service.claim_reward(self.unique_id, "3003")
        time.sleep(self.config.request_delay)
    
    def _task_comment(self, post_id: int):
        """任务: 评论帖子（针对指定帖子）"""
        logger.info("\n[任务] 评论帖子")
        comment_content = f"水 - {get_current_time()}"
        
        self.post_service.comment_post(
            self.unique_id, 
            post_id, 
            comment_content
        )
        time.sleep(self.config.request_delay)
    
    def _task_view_post_with_retry(self, post_id: int) -> bool:
        """任务: 浏览帖子（带重试，成功后才继续点赞等后续操作）"""
        logger.info("\n[任务] 浏览帖子")
        
        max_retries = self.config.max_retries
        retry_delay = self.config.retry_delay
        
        for attempt in range(1, max_retries + 1):
            if self.post_service.view_post(self.unique_id, post_id):
                return True
            
            if attempt < max_retries:
                logger.warning(
                    f"浏览帖子失败，{retry_delay}秒后重试 ({attempt}/{max_retries})..."
                )
                time.sleep(retry_delay)
        
        logger.error(f"浏览帖子失败，已重试 {max_retries} 次 (帖子ID: {post_id})")
        return False
    
    def _task_claim_rewards(self):
        """任务: 领取每日任务奖励（动态获取今日随机任务，批量领取可领取的）"""
        logger.info("\n[任务] 领取任务奖励")
        
        # 动态获取今日任务配置（任务每天随机，由服务器下发）
        task_data = self.task_service.get_task_list(self.unique_id)
        if not task_data:
            logger.warning("获取任务列表失败，跳过领奖（下次运行会自动重试）")
            return
        
        task_config = task_data.get("task_config") or []
        task_info = task_data.get("task_info") or []
        task_info_map = {
            str(t.get("task_id")): t
            for t in task_info if isinstance(t, dict)
        }
        
        # 筛选可领取任务：进度达标(progress>=times) 且 未领取(reward_time==0)
        claimable = []
        for task in task_config:
            task_id = str(task.get("id"))
            times = task.get("condition_times") or 0
            info = task_info_map.get(task_id)
            progress = info.get("task_progress", 0) if info else 0
            reward_time = info.get("reward_time", 0) if info else 0
            
            if reward_time > 0:
                continue  # 已领取
            if progress >= times:
                claimable.append(task_id)
        
        if not claimable:
            logger.info("今日暂无可以领取的任务奖励")
            return
        
        logger.info(f"今日可领取任务: {claimable}")
        self.task_service.claim_rewards_batch(self.unique_id, claimable)
    
    def _task_buy_item(self):
        """任务: 购买道具（shop_item_id=26, address_id=0 为固定任务商品）"""
        logger.info("\n[任务] 购买道具")
        
        self.task_service.buy_item(self.unique_id)
    
    def _task_share_post(self) -> bool:
        """分享帖子：发一个源帖 → 转发（from_post=源帖ID）→ 删除两个帖"""
        source_id = self._task_create_post()  # 源帖（带超时确认复用）
        if not source_id:
            return False
        
        share_id = self.post_service.share_post(self.unique_id, source_id)
        time.sleep(self.config.request_delay)
        
        # 清理：删除转发帖和源帖（发出即走，不等待响应）
        if share_id:
            self.post_service.delete_post(share_id)
            time.sleep(self.config.request_delay)
        self.post_service.delete_post(source_id)
        time.sleep(self.config.request_delay)
        return True
    
    def _task_create_and_process_post(self) -> bool:
        """创建新帖并完成 浏览→点赞→收藏→评论→删除 全流程（任务补足用）"""
        post_id = self._task_create_post()  # 带重试
        if not post_id:
            return False
        
        if self._task_view_post_with_retry(post_id):
            self._task_like(post_id)
            self._task_collect(post_id)
            self._task_comment(post_id)
        
        self._task_delete_post(post_id)
        return True
    
    def _calc_task_gaps(self, task_data: dict) -> dict:
        """解析任务列表，计算各类型任务缺口（仅 group==0 可自动化的每日任务）"""
        task_config = task_data.get("task_config") or []
        task_info = task_data.get("task_info") or []
        info_map = {
            str(t.get("task_id")): t
            for t in task_info if isinstance(t, dict)
        }
        
        gaps = {
            "sign": 0, "publish": 0, "like": 0, "follow": 0,
            "buy": 0, "stats": 0, "view": 0, "resonance": 0,
            "collect": 0, "share_post": 0, "share_record": 0
        }
        unsupported = set()  # 未支持的任务类型（有缺口但无法自动完成）
        
        for task in task_config:
            if task.get("group") != 0:
                continue
            task_id = str(task.get("id"))
            task_type = task.get("task_type")
            times = task.get("condition_times") or 0
            info = info_map.get(task_id)
            progress = info.get("task_progress", 0) if info else 0
            reward_time = info.get("reward_time", 0) if info else 0
            
            if reward_time > 0:
                continue
            gap = max(0, times - progress)
            if gap <= 0:
                continue
            
            if task_type == 1:              # 签到
                gaps["sign"] = max(gaps["sign"], gap)
            elif task_type in (2, 17):      # 发帖 / 发布图文贴
                gaps["publish"] += gap
            elif task_type == 3:            # 点赞
                gaps["like"] += gap
            elif task_type == 4:            # 关注
                gaps["follow"] += gap
            elif task_type == 5:            # 购买
                gaps["buy"] += gap
            elif task_type == 6:            # 查询战绩
                gaps["stats"] += gap
            elif task_type == 10:           # 浏览帖子
                gaps["view"] += gap
            elif task_type == 13:           # 收藏帖子
                gaps["collect"] += gap
            elif task_type == 14:           # 分享帖子
                gaps["share_post"] += gap
            elif task_type == 15:           # 分享战绩
                gaps["share_record"] += gap
            elif task_type == 16:           # 共鸣引擎
                gaps["resonance"] += gap
            else:
                # 未知/未支持的任务类型：提示而不是静默忽略
                unsupported.add((task_type, task.get("title") or ""))
        
        if unsupported:
            desc = ", ".join(f"{t}(type={ty})" for ty, t in sorted(unsupported))
            logger.warning(f"检测到暂不支持自动完成的任务类型: {desc}")
        
        return gaps
    
    def _execute_fulfillment(self, gaps: dict, task_data: dict):
        """执行任务补足动作"""
        # 1. 签到补足（daily_sign>0 说明今日已签到，跳过）
        if gaps["sign"] > 0:
            daily_sign = task_data.get("daily_sign", 0)
            if daily_sign > 0:
                logger.info("今日已签到，跳过签到补足")
            else:
                for _ in range(gaps["sign"]):
                    self.user_service.sign_in(self.unique_id)
                    time.sleep(self.config.request_delay)
        
        # 2. 共鸣引擎补足
        for _ in range(gaps["resonance"]):
            self.user_service.play_resonance_game()
            time.sleep(self.config.request_delay)
        
        # 3. 查询战绩补足
        for _ in range(gaps["stats"]):
            self.stats_service.query_performance(
                self.account_id, self.guid, "", self.role_id
            )
            time.sleep(self.config.request_delay)
            self.stats_service.query_history(self.role_id, 1, 1)
            time.sleep(self.config.request_delay)
        
        # 4. 购买补足
        for _ in range(gaps["buy"]):
            self.task_service.buy_item(self.unique_id)
            time.sleep(self.config.request_delay)
        
        # 5. 发帖补足（每个新帖走 发帖→浏览→点赞→收藏→评论→删除，同时贡献多个任务进度）
        need_posts = max(gaps["publish"], gaps["view"], gaps["like"], gaps["collect"])
        max_extra_posts = 5  # 上限（每帖贡献浏览+点赞+收藏+评论各1次；发太多帖有风控风险）
        post_count = min(need_posts, max_extra_posts)
        for _ in range(post_count):
            if self._task_create_and_process_post():
                gaps["publish"] = max(0, gaps["publish"] - 1)
                gaps["view"] = max(0, gaps["view"] - 1)
                gaps["like"] = max(0, gaps["like"] - 1)
                gaps["collect"] = max(0, gaps["collect"] - 1)
        
        # 6. 新帖不足以覆盖的浏览/点赞/收藏缺口：放弃（不再操作社区帖子，只在自己新帖上进行）
        remaining = max(gaps["view"], gaps["like"], gaps["collect"])
        if remaining > 0:
            logger.warning(
                f"新帖数量不足以完成浏览/点赞/收藏任务，仍有 {remaining} 次未补足"
                f"（可调大发帖上限 max_extra_posts）"
            )
        
        # 7. 分享帖子补足（转发帖子：发一个源帖 → 转发 → 删除两个帖）
        for _ in range(gaps["share_post"]):
            self._task_share_post()
        
        # 8. 分享战绩上报（TASK_ACTION，action=record_share 实测确认）
        for _ in range(gaps["share_record"]):
            self.user_service.share_action(SHARE_ACTION_RECORD)
            time.sleep(self.config.request_delay)
        if gaps["share_record"] > 0:
            logger.info(f"分享战绩上报完成 ({gaps['share_record']} 次)")
        
        # 9. 关注补足（对默认关注ID交替关注/取关）
        for i in range(gaps["follow"]):
            follow_type = 1 if i % 2 == 0 else 2
            self.social_service.follow_user(
                self.unique_id, self.config.default_follow_id, follow_type
            )
            time.sleep(self.config.request_delay)
    
    def _task_fulfill_daily_tasks(self):
        """任务完成闭环：检查任务完成情况 → 未完成的重试补足 → 复查，直到满足或达最大轮数。
        若某任务类型补足一轮后缺口无进展（任务 bug/服务器计数异常），自动标记为不可完成并停止补足"""
        logger.info("\n[任务] 任务完成检查与补足")
        
        max_rounds = 3        # 最大补足轮数
        stubborn = set()      # 补足无效的任务类型（缺口连续不减少）
        prev_gaps = None      # 上一轮补足前的缺口，用于检测进展
        
        for round_idx in range(1, max_rounds + 1):
            task_data = self.task_service.get_task_list(self.unique_id)
            if not task_data:
                logger.warning("获取任务列表失败，跳过本轮检查")
                return
            
            gaps = self._calc_task_gaps(task_data)
            
            # 检测补足无进展的类型（缺口未减少 = 操作对该任务无效）
            if prev_gaps is not None:
                for key in list(gaps):
                    if gaps[key] > 0 and gaps[key] >= prev_gaps.get(key, 0):
                        stubborn.add(key)
                        logger.warning(
                            f"任务类型[{key}] 补足后缺口未减少，判定为无法完成，停止补足"
                        )
                for key in stubborn:
                    gaps[key] = 0
            
            if sum(gaps.values()) == 0:
                if stubborn:
                    logger.warning(
                        f"本轮完成检查结束，无法自动完成的任务类型: {sorted(stubborn)}，"
                        f"其奖励将无法领取（可能是任务 bug 或需人工操作）"
                    )
                else:
                    logger.info(f"第{round_idx}轮检查: 所有可自动化任务均已完成")
                return
            
            logger.info(f"第{round_idx}轮检查: 任务缺口 {gaps}")
            self._execute_fulfillment(gaps, task_data)
            prev_gaps = gaps
        
        remaining = [k for k, v in prev_gaps.items() if v > 0] if prev_gaps else []
        logger.warning(
            f"经过 {max_rounds} 轮补足仍有任务未完成: {sorted(set(remaining) | stubborn)}"
        )
    
    def run(self):
        """运行任务"""
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"开始处理账号: {self.account.name}")
            logger.info(f"{'='*60}")
            logger.info(f"########## 脚本开始执行！ ########## {get_current_time()}")
            
            # 认证
            if not self.authenticate():
                logger.error(f"[{self.account.name}] 认证失败，跳过此账号")
                return False
            
            # 执行任务
            self.execute_daily_tasks()
            
            logger.info(f"########## 脚本全部执行完毕！ ########## {get_current_time()}")
            logger.info(f"[{self.account.name}] 任务完成")
            return True
            
        except Exception as e:
            logger.error(f"[{self.account.name}] 脚本执行异常: {e}", exc_info=True)
            return False
        
        finally:
            # 清理资源
            self.client.close()


def main():
    """主函数"""
    # 程序启动时只读取一次配置文件
    global_config = Config()
    
    logger.info("="*60)
    logger.info(f"检测到 {global_config.account_count} 个账号")
    logger.info("="*60)
    
    success_count = 0
    fail_count = 0
    
    # 遍历所有账号（使用已加载的配置，不再重复读取文件）
    for i, account in enumerate(global_config.accounts, 1):
        logger.info(f"\n{'#'*60}")
        logger.info(f"# 处理进度: {i}/{global_config.account_count}")
        logger.info(f"{'#'*60}")
        
        # 创建任务执行器，传入当前账号和全局配置
        runner = TaskRunner(account=account, global_config=global_config)
        success = runner.run()
        
        if success:
            success_count += 1
        else:
            fail_count += 1
        
        # 如果不是最后一个账号，等待一段时间
        if i < global_config.account_count:
            logger.info(f"\n等待 {global_config.account_delay} 秒后处理下一个账号...")
            time.sleep(global_config.account_delay)
    
    # 输出总结
    logger.info("\n" + "="*60)
    logger.info("所有账号处理完成！")
    logger.info(f"成功: {success_count} 个账号")
    logger.info(f"失败: {fail_count} 个账号")
    logger.info("="*60)
    
    # 返回退出码
    sys.exit(0 if fail_count == 0 else 1)


if __name__ == "__main__":
    main()

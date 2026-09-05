"""
300英雄宅基地自动任务工具 - 主程序
"""
import json
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

# 关注任务补足：拉取社区帖子作者候选的最大翻页数（作者不足时不再扩大骚扰面）
FOLLOW_CANDIDATE_MAX_PAGES = 5

# 图文帖任务(17)发帖附带图片：内置一张程序生成的 256x256 蓝色渐变 PNG（纯base64）。
# 不依赖外部文件、不含隐私内容；帖子发完即删。图片键与 content 中 [image|1] 标记对应。
TASK_POST_IMAGE_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAQAAAAEACAIAAADTED8xAAAFBklEQVR42u3TB5sIBByA8f9nEGVTtsO5w9mbs/c88+x59t6cvQkl"
    "QqSUCCWFKCkRIkV9m/7f432f5/cVfjHw8H8SVgw49K+ElQHeSFgx4OAbCSsDvJawov/B1xJW9D/wj4RlAMED7P9bwsoArySs6Lf/"
    "lYQV/fb9JWEZQPAAe19KWFG696WElQFeSFhRuueFhJUB/pSwonT3cwkr+u5+LmFlgGcSVvTd9UzCygBPJazos/OphJUB/pCwMsAT"
    "CSv67HgiYWWAxxJW9N7+WMLKAL9LWAYQPEDlIwkrelU+krCi17bfJKwM8KuEZQDBA2x9KGFFz60PJazoueUXCcsAogd4IGFFj80P"
    "JKwM8LOEFT02/SRhGUD0APclrOi+8b6ElQHuSVjRfcM9CSsD/ChhZYC7ElZ0W39XwsoAdySs6LbujoSVAW5LWNF13W0JK7qu/UHC"
    "MoDgAdZ8L2FlgFsSVnRZc0vCii6rv5OwDCB4gFU3JazovOqmhJUBvpWwovPKbyQsAwgeYMUNCSs6rbghYWWA6xJWdFp+XcLKANck"
    "rOi47JqElQG+lrAywFUJKzouvSphZYArElZ0WHJFwsoAX0lYBhA8wOLLEla0X3xZwor2i76UsDLAFxKWAQQPUHFJwoqSiksSVpQs"
    "/FzCMoDoAT6TsKJkwUUJK9otuChhRbv5n0pYBhA9wAUJK9rOuyBhZYDzEla0nXtewsoAn0hYGeCchBVt5pyTsDLAWQkr2sw+K2Fl"
    "gDMSVhTPPiNhRfGsjyWsDHBaworimaclrAxwSsKKopmnJKwomvGRhGUAwQNMPylhRevpJyWsDPChhBWtp30gYRlA8ADlJySsKCw/"
    "IWFlgOMSVhROPS5hZYBjEla0mnJMwsoA70tYGeCohBWtJh+VsDLAEQkrWk46ImFlgMMSlgEEDzDxkISVAQ5KWNFiwkEJKwMckLAM"
    "IHiAsv0SVhSU7ZewomD8PgnLAKIH2CthRcG4PRJWNB+3R8KK5mN3S1gGED3ALgkrmo3ZJWFlgJ0SVjQbvVPCygA7JKwMsF3Ciqaj"
    "tktYGaBSwoqmIyslrAywTcKKJiO3SVjRZMRWCSsDbJGwosnwLRJWBtgsYUXj4ZslrGg8bJOEZQDBAwzdKGFFo6EbJawMsEHCikZD"
    "1ktYBhA8wOB1ElY0HLxOwsoAayWsaDhorYSVAdZIWNFw4GoJKxoMXC1hZYBVElY0GLBKwsoAKyWseK//SgkrA6yQsAwgeIB+yyWs"
    "DLBMwop3S5dJWBlgqYRlAMED9F0iYUX9vkskrKjfZ7GEZQDRAyySsKJ+7woJK+r1rpCwol6vhRKWAUQPsEDCiro9F0hYGWC+hBV1"
    "e8yTsAwgeoC5ElbU6T5XwsoAcySsqNNtjoSVAWZLWFG722wJK2p3nSVhZYCZElbU7jJTwsoAMySsqNVlhoQVtTpPl7AMIHiATtMk"
    "rAxQLmFFzU7lElbU7DhVwjKA4AE6TJGwokaHKRJWBpgsYUWN9pMlrAwwScKKGiUTJayoXjJRwsoAEySsqN5ugoSVAcokrHinbZmE"
    "lQHGS1gGEDxAm3ESVgYYK2HF28VjJawMMEbCMoDgAYpGS1hRrWi0hBXVWo+SsDLASAnLAIIHKBwhYUXVwhESVlRtNVzCMoDoAYZJ"
    "WPFWy2ESVgYYKmHFWy2GSFgGED3AYAkrqhQMlrAywCAJK6o0HyRhZYCBEpYBhPY/FSAslgiJ1T8AAAAASUVORK5CYII="
)
TASK_POST_IMAGE_TYPE = "png"


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
        
        # 2. 签到
        self._task_sign_in()
        
        # 3. 游玩共鸣引擎
        self._task_play_resonance_game()
        
        # 4. 清理残留任务帖（上次运行发帖超时未删除的）
        self._task_cleanup_stale_posts()
        
        # 5. 发帖（创建新帖子，后续所有帖子操作都针对此帖；失败自动确认重试。
        #    今日含图文帖任务时带图发布，一次发帖同时覆盖图文帖与浏览/点赞等）
        post_id = self._task_create_post(with_image=self._task_need_image_post())
        
        # 6. 帖子相关操作（浏览 → 点赞 → 收藏 → 评论 → 删除）
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
        
        # 7. 购买道具
        self._task_buy_item()
        
        # 8. 任务驱动补足（读取今日随机任务，按缺口补足动作次数，含关注任务）
        self._task_fulfill_daily_tasks()
        
        # 9. 领取所有奖励（统一放到任务最后）
        self._task_claim_monthly_rewards()      # 月度累计签到奖励
        self._task_claim_resonance_reward()     # 共鸣引擎奖励
        self._task_claim_rewards()              # 每日任务奖励
        
        # 10. 兜底清理本次运行残留的任务帖（删除超时未删掉的）
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
    
    def _task_create_post(self, with_image: bool = False) -> Optional[int]:
        """
        任务: 发帖（失败自动确认重试，返回帖子ID供后续操作使用）
        
        Args:
            with_image: 是否附带图片（图文帖任务用）。带图时先上传内置图片，
                         content 加 [image|1] 标记、imgs 填上传文件名；上传失败降级为普通帖
        """
        logger.info("\n[任务] 发帖" + ("（带图）" if with_image else ""))
        title = f"这是一个任务帖子 - {get_current_time()}"
        brief = "这是一个任务帖子"
        content = "这是一个任务帖子"
        imgs = ""
        
        if with_image:
            img_name = self.post_service.upload_image(
                self.unique_id, TASK_POST_IMAGE_B64, TASK_POST_IMAGE_TYPE
            )
            if img_name:
                content = "[image|1] 这是一个任务帖子"
                imgs = json.dumps(
                    {"image|1": {"url": img_name, "extra": ""}},
                    ensure_ascii=False
                )
            else:
                logger.warning("图片上传失败，降级为普通发帖（图文帖任务将无法计数）")
        
        max_retries = self.config.max_retries
        retry_delay = self.config.retry_delay
        
        for attempt in range(1, max_retries + 1):
            post_id = self.post_service.create_post(
                self.unique_id,
                title,
                tabs_id=401,
                brief=brief,
                content=content,
                imgs=imgs
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
    
    def _fetch_follow_gap(self) -> Optional[int]:
        """
        获取当前"关注"任务的任务缺口（关注后复查计数用）

        Returns:
            关注任务缺口数（>=0），任务列表获取失败返回 None
        """
        task_data = self.task_service.get_task_list(self.unique_id)
        if not task_data:
            return None
        return self._calc_task_gaps(task_data).get("follow", 0)

    def _task_fulfill_follow(self, gap: int) -> None:
        """
        关注任务补足：从社区帖子列表动态找真实作者作为关注对象（每次不同的人），
        关注后复查任务进度确认是否被计数，然后立即取关，直到完成任务或候选耗尽。
        
        改版后服务器按"关注了不同的人"计数，固定关注同一ID不再有效；
        取关保证账号不残留关注，且同一作者次日仍可作为新关注对象。
        无进展（作者都已被关注过等）时留给上层无进展检测判定，不无限重试。
        """
        if gap <= 0:
            return
        logger.info(f"[任务] 关注任务补足 (缺口 {gap})")
        
        tried_uids = set()    # 本次已尝试过的作者，避免重复
        made = 0              # 被任务实际计数的关注次数
        orig_gap = gap
        
        for page in range(1, FOLLOW_CANDIDATE_MAX_PAGES + 1):
            posts = self.post_service.get_post_list(self.unique_id, pages=page)
            if not posts:
                break  # 拉不到更多帖子，候选耗尽
            
            for post in posts:
                if made >= orig_gap:
                    return
                uid = post.get("uid") or ""
                if not uid or uid == self.unique_id or uid in tried_uids:
                    continue  # 无作者 / 自己发的任务帖 / 重复作者
                tried_uids.add(uid)
                
                if not self.social_service.follow_user(self.unique_id, uid, 1):
                    continue  # 服务器拒绝（已关注过/当日已计），换下一位作者
                time.sleep(self.config.request_delay)
                
                # 每次关注后复查任务进度，确认是否真的被计数
                new_gap = self._fetch_follow_gap()
                
                # 无论是否计数都立即取关，保持账号不残留关注
                self.social_service.follow_user(self.unique_id, uid, 2)
                time.sleep(self.config.request_delay)
                
                if new_gap is not None and new_gap < gap:
                    gap = new_gap
                    made += 1
                    logger.info(f"关注成功已计数 (用户ID: {uid}, 剩余缺口 {gap})")
                # new_gap 未减少：该作者今日关注不计（去重），继续找下一位
                if made >= orig_gap:
                    return
        
        if made > 0:
            logger.info(f"关注补足完成 {made} 次，仍有 {gap} 次缺口等待复查")
        else:
            logger.warning(
                "关注补足无有效计数：候选作者均不可用或已关注过，"
                "若复查后缺口未减少将停止补足"
            )

    def _task_need_image_post(self) -> bool:
        """
        今日任务是否包含待完成的图文帖任务(17)（决定主流程发帖是否带图）

        Returns:
            有图文帖缺口返回 True；任务列表获取失败或缺口为0返回 False
        """
        task_data = self.task_service.get_task_list(self.unique_id)
        if not task_data:
            return False
        return self._calc_task_gaps(task_data).get("post_image", 0) > 0

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
    
    def _task_create_and_process_post(self, with_image: bool = False) -> bool:
        """创建新帖并完成 浏览→点赞→收藏→评论→删除 全流程（任务补足用）"""
        post_id = self._task_create_post(with_image=with_image)  # 带重试
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
            "sign": 0, "publish": 0, "post_image": 0, "like": 0, "follow": 0,
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
            elif task_type == 2:            # 发帖（任意帖子都计数）
                gaps["publish"] += gap
            elif task_type == 17:           # 发布图文贴（必须带图才能计数，发带图帖）
                gaps["post_image"] += gap
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
        
        # 5. 发帖补足（每个新帖走 发帖→浏览→点赞→收藏→评论→删除，同时贡献多个任务进度。
        #    存在图文帖任务(17)缺口时优先发带图帖——带图帖同时计入发帖与图文帖）
        need_posts = max(
            gaps["publish"], gaps["post_image"],
            gaps["view"], gaps["like"], gaps["collect"]
        )
        max_extra_posts = 5  # 上限（每帖贡献浏览+点赞+收藏+评论各1次；发太多帖有风控风险）
        post_count = min(need_posts, max_extra_posts)
        for _ in range(post_count):
            with_image = gaps["post_image"] > 0  # 还有图文帖缺口就发带图帖
            if self._task_create_and_process_post(with_image=with_image):
                gaps["publish"] = max(0, gaps["publish"] - 1)
                if with_image:
                    gaps["post_image"] = max(0, gaps["post_image"] - 1)
                gaps["view"] = max(0, gaps["view"] - 1)
                gaps["like"] = max(0, gaps["like"] - 1)
                gaps["collect"] = max(0, gaps["collect"] - 1)
        
        # 6. 新帖不足以覆盖的浏览/点赞/收藏/图文帖缺口：放弃（只在自己新帖上进行）
        remaining = max(gaps["view"], gaps["like"], gaps["collect"], gaps["post_image"])
        if remaining > 0:
            logger.warning(
                f"新帖数量不足以完成浏览/点赞/收藏/图文帖任务，仍有 {remaining} 次未补足"
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
        
        # 9. 关注任务补足（动态从社区帖子作者选人，关注成功计数后即时取关）
        if gaps["follow"] > 0:
            self._task_fulfill_follow(gaps["follow"])
    
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

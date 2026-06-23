"""
300英雄宅基地自动任务工具 - 主程序
"""
import sys
import time
from datetime import datetime
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
        
        # 1. 点赞和取消点赞
        self._task_like_and_unlike()
        
        # 2. 查询战绩
        self._task_query_stats()
        
        # 3. 关注和取消关注
        self._task_follow_and_unfollow()
        
        # 4. 签到
        self._task_sign_in()
        
        # 5. 评论
        self._task_comment()
        
        # 6. 发帖并删除
        self._task_create_and_delete_post()
        
        # 7. 浏览帖子
        self._task_view_post()
        
        # 8. 领取任务奖励
        self._task_claim_rewards()
        
        # 9. 购买任务
        self._task_buy_item()
        
        logger.info("=" * 50)
        logger.info("所有任务执行完毕")
        logger.info("=" * 50)
    
    def _task_like_and_unlike(self):
        """任务: 点赞和取消点赞"""
        logger.info("\n[任务] 点赞操作")
        post_id = self.config.default_post_id
        
        self.post_service.like_post(self.unique_id, post_id, 1)
        time.sleep(self.config.request_delay)
        
        self.post_service.like_post(self.unique_id, post_id, 2)
    
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
    
    def _task_comment(self):
        """任务: 评论帖子"""
        logger.info("\n[任务] 评论帖子")
        comment_content = f"水 - {get_current_time()}"
        
        self.post_service.comment_post(
            self.unique_id, 
            self.config.default_post_id, 
            comment_content
        )
        time.sleep(self.config.request_delay)
    
    def _task_create_and_delete_post(self):
        """任务: 发帖并删除"""
        logger.info("\n[任务] 发帖并删除")
        
        title = f"这是一个任务帖子 - {get_current_time()}"
        brief = "这是一个任务帖子"
        content = "这是一个任务帖子"
        
        self.post_service.create_and_delete_post(
            self.unique_id,
            title,
            tabs_id=401,
            brief=brief,
            content=content,
            wait_time=10
        )
        time.sleep(self.config.request_delay)
    
    def _task_view_post(self):
        """任务: 浏览帖子"""
        logger.info("\n[任务] 浏览帖子")
        
        self.post_service.view_post(self.unique_id, self.config.default_post_id)
    
    def _task_claim_rewards(self):
        """任务: 领取任务奖励"""
        logger.info("\n[任务] 领取任务奖励")
        
        task_ids = self.config.task_ids
        self.task_service.claim_all_rewards(self.unique_id, task_ids)
    
    def _task_buy_item(self):
        """任务: 购买道具"""
        logger.info("\n[任务] 购买道具")
        
        self.task_service.buy_item(self.unique_id)
    
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

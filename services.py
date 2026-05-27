"""
300英雄宅基地自动任务工具 - 业务服务模块
"""
import time
import json
from typing import Dict, Any, Optional
from logger import logger
from config_manager import Config
from api_client import APIClient


class UserService:
    """用户相关服务"""
    
    def __init__(self, client: APIClient, config: Config):
        self.client = client
        self.config = config
    
    def validate_token(self) -> Optional[Dict[str, Any]]:
        """
        验证token
        
        Returns:
            解析后的MSG数据，失败返回None
        """
        try:
            response = self.client.request(1004, {"token": self.config.token})
            
            if not response.get("MSG"):
                logger.error("Token无效或已过期")
                return None
            
            msg_data = json.loads(response["MSG"])
            logger.info("Token验证成功")
            return msg_data
            
        except Exception as e:
            logger.error(f"Token验证失败: {e}")
            return None
    
    def sign_in(self, unique_id: str) -> bool:
        """
        签到
        
        Args:
            unique_id: 用户唯一ID
        
        Returns:
            是否成功
        """
        try:
            response = self.client.request(1073, {
                "unique_id": unique_id
            })
            
            if response.get("RES") == 0:
                logger.info("签到成功")
                return True
            else:
                logger.warning(f"签到失败: {response}")
                return False
                
        except Exception as e:
            logger.error(f"签到异常: {e}")
            return False


class PostService:
    """帖子相关服务"""
    
    def __init__(self, client: APIClient, config: Config):
        self.client = client
        self.config = config
    
    def like_post(self, unique_id: str, posts_id: int, like_type: int) -> bool:
        """
        点赞/取消点赞
        
        Args:
            unique_id: 用户唯一ID
            posts_id: 帖子ID
            like_type: 1=点赞, 2=取消点赞
        
        Returns:
            是否成功
        """
        action = "点赞" if like_type == 1 else "取消点赞"
        try:
            response = self.client.request(1018, {
                "unique_id": unique_id,
                "posts_id": posts_id,
                "like_type": like_type
            })
            
            if response.get("RES") == 0:
                logger.info(f"{action}成功 (帖子ID: {posts_id})")
                return True
            else:
                logger.warning(f"{action}失败: {response}")
                return False
                
        except Exception as e:
            logger.error(f"{action}异常: {e}")
            return False
    
    def comment_post(self, unique_id: str, posts_id: int, content: str) -> bool:
        """
        评论帖子
        
        Args:
            unique_id: 用户唯一ID
            posts_id: 帖子ID
            content: 评论内容
        
        Returns:
            是否成功
        """
        try:
            response = self.client.request(1028, {
                "unique_id": unique_id,
                "posts_id": posts_id,
                "content": content,
                "imgs": "",
                "links": "{}",
                "ats": "{}",
                "extras": "{}"
            })
            
            if response.get("RES") == 0:
                logger.info(f"评论成功 (帖子ID: {posts_id})")
                return True
            else:
                logger.warning(f"评论失败: {response}")
                return False
                
        except Exception as e:
            logger.error(f"评论异常: {e}")
            return False
    
    def create_post(self, unique_id: str, title: str, tabs_id: int, 
                   brief: str, content: str) -> Optional[int]:
        """
        创建帖子
        
        Args:
            unique_id: 用户唯一ID
            title: 标题
            tabs_id: 版块ID
            brief: 简介
            content: 内容
        
        Returns:
            帖子ID，失败返回None
        """
        try:
            response = self.client.request(1017, {
                "unique_id": unique_id,
                "title": title,
                "tabs_id": tabs_id,
                "brief": brief,
                "content": content,
                "imgs": "",
                "links": "{}",
                "topics": "",
                "is_open": True,
                "ats": "{}",
                "from_post": 0,
                "is_vote": False,
                "extras": "{}"
            })
            
            if response.get("RES") == 0 and "MSG" in response:
                posts_id = response["MSG"]["Posts_Id"]
                logger.info(f"发帖成功 (帖子ID: {posts_id})")
                return posts_id
            else:
                logger.warning(f"发帖失败: {response}")
                return None
                
        except Exception as e:
            logger.error(f"发帖异常: {e}")
            return None
    
    def delete_post(self, post_id: int, delete_type: int = 1) -> bool:
        """
        删除帖子
        
        Args:
            post_id: 帖子ID
            delete_type: 删除类型
        
        Returns:
            是否成功
        """
        try:
            response = self.client.request(1085, {
                "type": delete_type,
                "value": post_id
            })
            
            if response.get("RES") == 0:
                logger.info(f"删除帖子成功 (帖子ID: {post_id})")
                return True
            else:
                logger.warning(f"删除帖子失败: {response}")
                return False
                
        except Exception as e:
            logger.error(f"删除帖子异常: {e}")
            return False
    
    def view_post(self, unique_id: str, post_id: int) -> bool:
        """
        浏览帖子
        
        Args:
            unique_id: 用户唯一ID
            post_id: 帖子ID
        
        Returns:
            是否成功
        """
        try:
            response = self.client.request(1056, {
                "unique_id": unique_id,
                "post_id": post_id
            })
            
            if response.get("RES") == 0:
                logger.info(f"浏览帖子成功 (帖子ID: {post_id})")
                return True
            else:
                logger.warning(f"浏览帖子失败: {response}")
                return False
                
        except Exception as e:
            logger.error(f"浏览帖子异常: {e}")
            return False
    
    def create_and_delete_post(self, unique_id: str, title: str, tabs_id: int,
                              brief: str, content: str, wait_time: int = 10) -> bool:
        """
        创建帖子并延迟删除
        
        Args:
            unique_id: 用户唯一ID
            title: 标题
            tabs_id: 版块ID
            brief: 简介
            content: 内容
            wait_time: 等待时间(秒)
        
        Returns:
            是否成功
        """
        posts_id = self.create_post(unique_id, title, tabs_id, brief, content)
        
        if not posts_id:
            return False
        
        logger.info(f"等待{wait_time}秒后删除帖子...")
        time.sleep(wait_time)
        
        return self.delete_post(posts_id)


class SocialService:
    """社交相关服务"""
    
    def __init__(self, client: APIClient, config: Config):
        self.client = client
        self.config = config
    
    def follow_user(self, unique_id: str, follow_id: str, follow_type: int) -> bool:
        """
        关注/取消关注用户
        
        Args:
            unique_id: 用户唯一ID
            follow_id: 被关注用户ID
            follow_type: 1=关注, 2=取消关注
        
        Returns:
            是否成功
        """
        action = "关注" if follow_type == 1 else "取消关注"
        try:
            response = self.client.request(1029, {
                "unique_id": unique_id,
                "follow_id": follow_id,
                "follow_type": follow_type
            })
            
            if response.get("RES") == 0:
                logger.info(f"{action}成功 (用户ID: {follow_id})")
                return True
            else:
                logger.warning(f"{action}失败: {response}")
                return False
                
        except Exception as e:
            logger.error(f"{action}异常: {e}")
            return False


class TaskService:
    """任务相关服务"""
    
    def __init__(self, client: APIClient, config: Config):
        self.client = client
        self.config = config
    
    def claim_reward(self, unique_id: str, task_id: str) -> bool:
        """
        领取任务奖励
        
        Args:
            unique_id: 用户唯一ID
            task_id: 任务ID
        
        Returns:
            是否成功
        """
        try:
            response = self.client.request(1074, {
                "unique_id": unique_id,
                "task_id_list": task_id
            })
            
            if response.get("RES") == 0:
                logger.info(f"领取任务奖励成功 (任务ID: {task_id})")
                return True
            else:
                logger.warning(f"领取任务奖励失败 (任务ID: {task_id}): {response}")
                return False
                
        except Exception as e:
            logger.error(f"领取任务奖励异常 (任务ID: {task_id}): {e}")
            return False
    
    def claim_all_rewards(self, unique_id: str, task_ids: list) -> Dict[str, bool]:
        """
        批量领取任务奖励
        
        Args:
            unique_id: 用户唯一ID
            task_ids: 任务ID列表
        
        Returns:
            每个任务的执行结果
        """
        results = {}
        for task_id in task_ids:
            success = self.claim_reward(unique_id, str(task_id))
            results[str(task_id)] = success
            time.sleep(self.config.request_delay)
        
        success_count = sum(1 for v in results.values() if v)
        logger.info(f"任务奖励领取完成: {success_count}/{len(task_ids)} 成功")
        
        return results


class StatsService:
    """战绩相关服务"""
    
    def __init__(self, client: APIClient, config: Config):
        self.client = client
        self.config = config
    
    def query_performance(self, account_id: str, 
                         guid: str, role_name: str, role_id: int) -> Optional[Dict]:
        """
        查询战绩
        
        Args:
            account_id: 账号ID
            guid: GUID
            role_name: 角色名
            role_id: 角色ID
        
        Returns:
            战绩数据，失败返回None
        """
        try:
            response = self.client.request(1009, {
                "AccountID": account_id,
                "Guid": guid,
                "RoleName": role_name,
                "RoleID": role_id
            })
            
            if response.get("RES") == 0:
                logger.info("查询战绩成功")
                return response
            else:
                logger.warning(f"查询战绩失败: {response}")
                return None
                
        except Exception as e:
            logger.error(f"查询战绩异常: {e}")
            return None
    
    def query_history(self, role_id: int, 
                     match_type: int, search_index: int) -> Optional[Dict]:
        """
        查询历史战绩
        
        Args:
            role_id: 角色ID
            match_type: 比赛类型
            search_index: 搜索索引
        
        Returns:
            历史战绩数据，失败返回None
        """
        try:
            response = self.client.request(1011, {
                "RoleID": role_id,
                "MatchType": match_type,
                "SearchIndex": search_index
            })
            
            if response.get("RES") == 0:
                logger.info("查询历史战绩成功")
                return response
            else:
                logger.warning(f"查询历史战绩失败: {response}")
                return None
                
        except Exception as e:
            logger.error(f"查询历史战绩异常: {e}")
            return None

"""
300英雄宅基地自动任务工具 - 业务服务模块
"""
import json
from typing import Dict, Any, Optional
from logger import logger
from config_manager import Config
from api_client import APIClient
from msgid import *


def _extract_msg(response: Dict[str, Any]) -> Any:
    """
    从响应中提取MSG数据，兼容dict和JSON字符串两种格式

    Args:
        response: API响应

    Returns:
        MSG解析后的数据，无法解析返回None
    """
    msg = response.get("MSG")
    if isinstance(msg, str):
        try:
            return json.loads(msg)
        except (json.JSONDecodeError, TypeError):
            return None
    return msg


def _extract_items(response: Any) -> list:
    """
    从列表类接口响应中提取帖子条目，兼容三种格式：
    1. 数组 [ {...}, {...} ]
    2. 对象映射 {"1": {...}, "2": {...}}
    3. 带RES包装的 {"RES":0, "1": {...}}（跳过 RES/ERR/MSG 键）

    Args:
        response: API响应

    Returns:
        条目列表（dict 元素）
    """
    if isinstance(response, list):
        return [v for v in response if isinstance(v, dict)]
    if isinstance(response, dict):
        return [
            v for k, v in response.items()
            if k not in ("RES", "ERR", "MSG") and isinstance(v, dict)
        ]
    return []


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
            response = self.client.request(ACCOUNT_LOGIN, {})
            
            if not response.get("MSG"):
                logger.error("Token无效或已过期")
                return None
            
            msg_data = _extract_msg(response)
            if msg_data is None:
                logger.error("Token验证失败: MSG解析失败")
                return None
            
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
            response = self.client.request(RECEIVE_TASK_REWARD, {
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
    
    def play_resonance_game(self) -> bool:
        """
        游玩共鸣引擎

        Returns:
            是否成功
        """
        try:
            response = self.client.request(TASK_ACTION, {
                "action": "resonance_game"
            })
            
            if response.get("RES") == 0:
                logger.info("共鸣引擎游玩成功")
                return True
            else:
                logger.warning(f"共鸣引擎游玩失败: {response}")
                return False
                
        except Exception as e:
            logger.error(f"共鸣引擎游玩异常: {e}")
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
            response = self.client.request(LIKE_POST, {
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
            response = self.client.request(GET_PERSONAL_POSTS, {
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
            response = self.client.request(PUBLISH_POST, {
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
                msg_data = _extract_msg(response)
                if msg_data is None:
                    logger.warning(f"发帖失败: MSG解析失败: {response}")
                    return None
                posts_id = msg_data.get("Posts_Id")
                if posts_id is None:
                    logger.warning(f"发帖失败: 未获取到帖子ID: {response}")
                    return None
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
            response = self.client.request(DELETE_POST_REPLY_DETAIL, {
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
            response = self.client.request(GET_POST_DETAIL_CACHE, {
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
    
    def get_post_list(self, unique_id: str, tabs_id: int = 401,
                      pages: int = 1, post_type: int = 1) -> list:
        """
        获取社区帖子列表（用于任务补足的点赞/浏览目标）
        
        Args:
            unique_id: 用户唯一ID
            tabs_id: 版块ID
            pages: 页码
            post_type: 帖子类型
        
        Returns:
            帖子列表 [{"postid": int, "uid": str}]
        """
        try:
            response = self.client.request(GET_POST_LIST, {
                "unique_id": unique_id,
                "tabs_id": tabs_id,
                "pages": pages,
                "type": post_type
            })
            
            posts = []
            items = _extract_items(response)
            for value in items:
                if value and value.get("id"):
                    posts.append({
                        "postid": int(value["id"]),
                        "uid": (value.get("userInfo") or {}).get("uid", "")
                    })
            
            if posts:
                logger.info(f"获取帖子列表成功 ({len(posts)} 条)")
            else:
                logger.warning(f"获取帖子列表失败或无数据: {response}")
            return posts
                
        except Exception as e:
            logger.error(f"获取帖子列表异常: {e}")
            return []
    
    def get_my_posts(self, unique_id: str, pages: int = 1) -> list:
        """
        获取自己发布的帖子列表（用于清理残留任务帖、发帖超时确认）
        
        Args:
            unique_id: 用户唯一ID
            pages: 页码
        
        Returns:
            帖子列表 [{"postid": int, "title": str, "brief": str}]
        """
        try:
            response = self.client.request(GET_FANS_LIST, {
                "unique_id": unique_id,
                "other_unique_id": unique_id,
                "pages": pages
            })
            
            posts = []
            items = _extract_items(response)
            for value in items:
                if value and value.get("id"):
                    posts.append({
                        "postid": int(value["id"]),
                        "title": value.get("title") or "",
                        "brief": value.get("brief") or ""
                    })
            
            if posts:
                logger.info(f"获取我的帖子列表成功 ({len(posts)} 条)")
            else:
                logger.warning(f"获取我的帖子列表失败或无数据: {response}")
            return posts
                
        except Exception as e:
            logger.error(f"获取我的帖子列表异常: {e}")
            return []


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
            response = self.client.request(GET_PERSONAL_INFO, {
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
    
    def get_task_list(self, unique_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务列表（服务器每日随机下发）
        
        Args:
            unique_id: 用户唯一ID
        
        Returns:
            返回 MSG 数据（含 task_config / task_info / daily_sign），失败返回None
        """
        try:
            response = self.client.request(GET_TASK_LIST, {
                "unique_id": unique_id
            })
            
            if response.get("RES") == 0:
                return response.get("MSG") or {}
            else:
                logger.warning(f"获取任务列表失败: {response}")
                return None
                
        except Exception as e:
            logger.error(f"获取任务列表异常: {e}")
            return None
    
    def claim_reward(self, unique_id: str, task_id: str) -> bool:
        """
        领取任务奖励（单个任务）

        Args:
            unique_id: 用户唯一ID
            task_id: 任务ID
        
        Returns:
            是否成功
        """
        try:
            response = self.client.request(GET_BAG_LIST, {
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
    
    def claim_rewards_batch(self, unique_id: str, task_ids: list) -> bool:
        """
        批量领取任务奖励（一次请求，task_id_list 逗号分隔）
        
        Args:
            unique_id: 用户唯一ID
            task_ids: 任务ID列表
        
        Returns:
            是否成功
        """
        if not task_ids:
            logger.warning("批量领取失败: 任务ID列表为空")
            return False
        
        task_id_list = ",".join(str(t) for t in task_ids)
        return self.claim_reward(unique_id, task_id_list)
    
    def buy_item(self, unique_id: str, shop_item_id: int = 26, address_id: int = 0) -> bool:
        """
        购买任务（商店购买道具）
        
        Args:
            unique_id: 用户唯一ID
            shop_item_id: 商品ID，默认26
            address_id: 地址ID，默认0
        
        Returns:
            是否成功
        """
        try:
            response = self.client.request(GET_STORE_LIST, {
                "unique_id": unique_id,
                "shop_item_id": shop_item_id,
                "address_id": address_id
            })
            
            if response.get("RES") == 0:
                logger.info(f"购买成功 (商品ID: {shop_item_id})")
                return True
            else:
                logger.warning(f"购买失败 (商品ID: {shop_item_id}): {response}")
                return False
                
        except Exception as e:
            logger.error(f"购买异常 (商品ID: {shop_item_id}): {e}")
            return False


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
            response = self.client.request(GET_ROLE_INFO, {
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
            response = self.client.request(GET_USER_INFO, {
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

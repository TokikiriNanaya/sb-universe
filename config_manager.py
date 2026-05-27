"""
300英雄宅基地自动任务工具 - 配置模块
"""
import yaml
from typing import Dict, Any


class Config:
    """配置管理类"""
    
    def __init__(self, config_path: str = 'config.yaml'):
        self.config_path = config_path
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载YAML配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"配置文件格式错误: {e}")
    
    @property
    def token(self) -> str:
        """获取token"""
        token = self._config.get('token')
        if not token:
            raise ValueError("Token未配置，请在config.yaml中设置")
        return token
    
    @property
    def api_base_url(self) -> str:
        """获取API基础URL"""
        return self._config.get('api_base_url', 'https://300zjd.tygms.cn/')
    
    @property
    def default_post_id(self) -> int:
        """获取默认帖子ID"""
        return self._config.get('default_post_id', 8403)
    
    @property
    def default_follow_id(self) -> str:
        """获取默认关注用户ID"""
        return self._config.get('default_follow_id', 'p492210972677771264')
    
    @property
    def task_ids(self) -> list:
        """获取任务ID列表"""
        return self._config.get('task_ids', list(range(1, 10)))
    
    @property
    def request_delay(self) -> float:
        """获取请求延迟时间(秒)"""
        return self._config.get('request_delay', 1.0)
    
    @property
    def max_retries(self) -> int:
        """获取最大重试次数"""
        return self._config.get('max_retries', 3)
    
    @property
    def timeout(self) -> int:
        """获取请求超时时间(秒)"""
        return self._config.get('timeout', 30)

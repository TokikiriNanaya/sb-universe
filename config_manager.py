"""
300英雄宅基地自动任务工具 - 配置模块
"""
import yaml
from typing import Dict, Any, List, Optional


class AccountConfig:
    """单个账号配置"""
    
    def __init__(self, name: str, token: str):
        self.name = name
        self.token = token
    
    def __repr__(self):
        return f"AccountConfig(name='{self.name}', token='{self.token[:8]}...')"


class Config:
    """配置管理类"""
    
    def __init__(self, config_path: str = 'config.yaml'):
        self.config_path = config_path
        self._config = self._load_config()
        self._accounts = self._parse_accounts()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载YAML配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"配置文件格式错误: {e}")
    
    def _parse_accounts(self) -> List[AccountConfig]:
        """解析账号配置"""
        accounts = []
        
        # 从accounts列表中解析
        if 'accounts' in self._config and self._config['accounts']:
            for acc in self._config['accounts']:
                name = acc.get('name', f'账号{len(accounts)+1}')
                token = acc.get('token')
                if token:
                    accounts.append(AccountConfig(name=name, token=token))
        
        if not accounts:
            raise ValueError("未配置任何账号，请在config.yaml的accounts中添加账号")
        
        return accounts
    
    @property
    def accounts(self) -> List[AccountConfig]:
        """获取所有账号配置"""
        return self._accounts
    
    @property
    def account_count(self) -> int:
        """获取账号数量"""
        return len(self._accounts)
    
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
    def account_delay(self) -> float:
        """获取账号间延迟时间(秒)"""
        return self._config.get('account_delay', 5.0)
    
    @property
    def max_retries(self) -> int:
        """获取最大重试次数"""
        return self._config.get('max_retries', 3)
    
    @property
    def timeout(self) -> int:
        """获取请求超时时间(秒)"""
        return self._config.get('timeout', 30)

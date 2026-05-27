"""
300英雄宅基地自动任务工具 - HTTP客户端模块
"""
import requests
import ssl
import json
from requests.adapters import HTTPAdapter
from typing import Dict, Any, Optional
from logger import logger
from config_manager import Config


class PyOpenSSLAdapter(HTTPAdapter):
    """自定义SSL适配器"""
    
    def init_poolmanager(self, *args, **kwargs):
        context = ssl.create_default_context()
        context.load_default_certs()
        kwargs['ssl_context'] = context
        return super().init_poolmanager(*args, **kwargs)


class APIClient:
    """API客户端类"""
    
    def __init__(self, config: Config):
        self.config = config
        self.session = self._create_session()
        self.headers = self._get_headers()
    
    def _create_session(self) -> requests.Session:
        """创建并配置session"""
        session = requests.Session()
        session.mount('https://', PyOpenSSLAdapter())
        return session
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'Origin': 'https://300universe.tygms.com',
            'Pragma': 'no-cache',
            'Referer': 'https://300universe.tygms.com/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'cross-site',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) '
                         'AppleWebKit/537.36 (KHTML, like Gecko) '
                         'Chrome/134.0.0.0 Mobile Safari/537.36',
            'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
        }
    
    def request(self, msgid: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送API请求
            
        Args:
            msgid: 消息ID
            data: 请求数据
            
        Returns:
            解析后的响应数据
        """
        # 自动添加token
        data['token'] = self.config._config.get('token')
        data['msgid'] = msgid
        
        response = None
        try:
            response = self.session.post(
                self.config.api_base_url,
                headers=self.headers,
                json=data,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败 (msgid={msgid}): {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败 (msgid={msgid}): {e}")
            if response is not None:
                logger.debug(f"响应内容: {response.text}")
            raise
    
    def close(self):
        """关闭session"""
        self.session.close()

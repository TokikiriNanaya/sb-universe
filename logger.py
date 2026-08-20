"""
300英雄宅基地自动任务工具 - 日志模块
"""
import logging


def setup_logger(name: str = 'SBUniverse', log_level: int = logging.INFO) -> logging.Logger:
    """
    配置日志记录器
    
    Args:
        name: 日志记录器名称
        log_level: 日志级别
    
    Returns:
        配置好的logger实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # 避免重复添加handler
    if logger.handlers:
        return logger
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    # 设置日志格式
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    return logger


# 创建全局logger实例
logger = setup_logger()

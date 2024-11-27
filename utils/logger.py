import logging
import os
from datetime import datetime

import pytz

DEFAULT_LOG_DIR="./logs"
DEFAULT_LOG_TIME_ZONE='Asia/Shanghai'
DEFAULT_LOG_NAME_FORMAT='%Y-%m-%d_%H-%M'

def init_logger(name:str="root"):
    """
    Initialize the logger, configure log level, format, and output methods.
    初始化日志记录器，配置日志级别、格式和输出方式。
    :return: Configured logger object
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s: - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    # 获取当前日期和时间
    now = datetime.now(tz=pytz.timezone(DEFAULT_LOG_TIME_ZONE))
    # 生成文件名
    log_filename = now.strftime(DEFAULT_LOG_NAME_FORMAT) + '.log'
    # 使用FileHandler输出到文件
    os.makedirs(DEFAULT_LOG_DIR, exist_ok=True)
    fh = logging.FileHandler(os.path.join(DEFAULT_LOG_DIR, log_filename))
    fh.setFormatter(formatter)
    # 使用StreamHandler输出到屏幕
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    # 添加两个Handler
    logger.handlers = []
    logger.addHandler(ch)
    logger.addHandler(fh)

    return logger
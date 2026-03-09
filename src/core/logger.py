import logging
import warnings
from logging.handlers import TimedRotatingFileHandler
from config.settings import APP_DATA_DIR
import re

class PrivacyFormatter(logging.Formatter):
    """自定义日志格式化器，在最终输出前通过正则抹除所有的本地用户路径（包括异常堆栈中的物理路径）"""
    def __init__(self, fmt=None):
        super().__init__(fmt)
        self.pattern = re.compile(r"(?i)([A-Z]:\\Users\\[^\\]+)")

    def format(self, record):
        original_msg = super().format(record)
        return self.pattern.sub(r"C:\\Users\\%USERNAME%", original_msg)

# 屏蔽 requests/urllib3 由于系统依赖打包带来的版本不匹配告警
warnings.filterwarnings("ignore", message=".*urllib3.*doesn't match a supported version.*")
try:
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    warnings.simplefilter('ignore', InsecureRequestWarning)
except ImportError:
    pass


def setup_logger(name="zenclean"):
    log_dir = APP_DATA_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "zenclean.log"
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # 避免重复绑定 handler
    if not logger.handlers:
        # 每天轮转，保留 7 天
        file_handler = TimedRotatingFileHandler(
            log_file, when="midnight", interval=1, backupCount=7, encoding="utf-8"
        )
        file_handler.setLevel(logging.INFO)
        file_formatter = PrivacyFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = PrivacyFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        # ── 启动时主动清扫过期日志 ─────────────────────────────────────
        # TimedRotatingFileHandler 仅在下一次轮转（子夜）触发时删旧备份。
        # 如果用户长期未打开软件，中间堆积的日志不会被清理。
        # 因此在每次启动时主动扫描，删除超过 7 天的备份文件。
        import os
        import time
        _MAX_AGE_SECONDS = 7 * 24 * 3600  # 7 天
        try:
            now = time.time()
            for f in log_dir.iterdir():
                # 匹配 zenclean.log.YYYY-MM-DD 等备份格式
                if f.is_file() and f.name.startswith(log_file.name) and f != log_file:
                    if now - f.stat().st_mtime > _MAX_AGE_SECONDS:
                        f.unlink(missing_ok=True)
        except Exception:
            pass  # 清理失败不影响主流程

    return logger

logger = setup_logger()

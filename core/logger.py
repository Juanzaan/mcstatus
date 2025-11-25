import logging
import json
import os
import re
from logging.handlers import RotatingFileHandler
from .config_loader import ConfigLoader

class LogSanitizer(logging.Filter):
    """Filter to scrub sensitive data from logs"""
    SENSITIVE_PATTERNS = [
        r"api_key=['\"][^'\"]+['\"]",
        r"password=['\"][^'\"]+['\"]",
        r"token=['\"][^'\"]+['\"]"
    ]
    
    def filter(self, record):
        msg = record.getMessage()
        if not isinstance(msg, str):
            return True
        for pattern in self.SENSITIVE_PATTERNS:
            msg = re.sub(pattern, "***REDACTED***", msg)
        record.msg = msg
        return True

class JSONFormatter(logging.Formatter):
    """Format logs as JSON for ingestion systems"""
    def format(self, record):
        log_obj = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno
        }
        if hasattr(record, 'context'):
            log_obj.update(record.context)
        return json.dumps(log_obj)

def setup_logger(name: str, log_file: str = None) -> logging.Logger:
    """
    Setup a logger instance with configuration from centralized config.
    """
    config = ConfigLoader.load()
    log_cfg = config.get('logging', {})
    
    level_str = log_cfg.get('level', 'INFO')
    level = getattr(logging, level_str.upper(), logging.INFO)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if logger.handlers:
        return logger

    # Ensure logs dir exists
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Rotating File Handler
        max_mb = log_cfg.get('file_rotation_mb', 10)
        backup_count = log_cfg.get('backup_count', 5)
        
        fh = RotatingFileHandler(
            log_file, 
            maxBytes=max_mb * 1024 * 1024, 
            backupCount=backup_count, 
            encoding='utf-8'
        )
        
        if log_cfg.get('json_format', True):
            fh.setFormatter(JSONFormatter())
        else:
            fh.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s'))
            
        if log_cfg.get('sanitize', True):
            fh.addFilter(LogSanitizer())
            
        logger.addHandler(fh)

    # Console Handler
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s'))
    if log_cfg.get('sanitize', True):
        ch.addFilter(LogSanitizer())
    logger.addHandler(ch)

    return logger

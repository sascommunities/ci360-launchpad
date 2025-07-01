import logging
import logging.config
import os

def setup_logging(default_path='logger/logger.ini', default_level=logging.INFO, env_key='LOG_CFG'):
    """Setup logging configuration"""
    path = default_path
    value = os.getenv(env_key, None)
    if value:
        path = value
    if os.path.exists(path):
        logging.config.fileConfig(path)
    else:
        logging.basicConfig(level=default_level)

    # Ensure log directory exists
    log_dir = os.path.dirname('logs/BulkCustomTaskDataExportApplication.log')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        logging.info(f"Created log directory: {log_dir}")

# Initialize logging configuration when the module is imported
setup_logging()

def get_logger(name='root'):
    return logging.getLogger(name)

def get_log_level():
    return {
        'CRITICAL': logging.CRITICAL,
        'ERROR': logging.ERROR,
        'WARNING': logging.WARNING,
        'INFO': logging.INFO,
        'DEBUG': logging.DEBUG,
        'NOTSET': logging.NOTSET
    }

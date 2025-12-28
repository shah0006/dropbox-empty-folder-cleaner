import os
import logging
import sys
import traceback
from datetime import datetime

class DetailedFormatter(logging.Formatter):
    """Custom formatter to include more details on errors."""
    def format(self, record):
        formatted = super().format(record)
        if record.levelno >= logging.ERROR and record.exc_info:
            # If there's exception info, it's already included by super().format 
            # if the format string has %(message)s and we use logger.exception()
            pass
        return formatted

def setup_logger(name, log_prefix='dropbox_cleaner'):
    """
    Set up a robust logger with file and console handlers.
    File: logs/{prefix}_{timestamp}.log (DEBUG level)
    Console: stdout (INFO level)
    """
    # Create logs directory
    os.makedirs('logs', exist_ok=True)
    
    # Configure logging format
    # Includes [module:line] for easier tracing
    LOG_FORMAT = '%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] %(message)s'
    LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_filename = os.path.join('logs', f"{log_prefix}_{timestamp}.log")
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Avoid duplicate handlers if already setup
    if not logger.handlers:
        # File handler (Detailed DEBUG logging)
        try:
            file_handler = logging.FileHandler(log_filename, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"Warning: Could not create log file {log_filename}: {e}")
        
        # Console handler (Clean INFO logging)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
        logger.addHandler(console_handler)
    
    return logger, log_filename

def format_api_error(e):
    """
    Format a Dropbox ApiError for robust logging.
    Extracts structured error data, request IDs, and user-facing messages.
    """
    error_msg = f"API Error: {str(e)}"
    
    try:
        if hasattr(e, 'error'):
            # Dropbox API errors often have a structured 'error' attribute
            error_msg += f"\n  - Error Detail: {e.error}"
        
        if hasattr(e, 'user_message_text') and e.user_message_text:
            error_msg += f"\n  - User Message: {e.user_message_text}"
            
        if hasattr(e, 'request_id') and e.request_id:
            error_msg += f"\n  - Request ID: {e.request_id}"
            
        # For certain error types, we can be even more specific
        from dropbox.exceptions import ApiError
        if isinstance(e, ApiError):
            if hasattr(e.error, 'is_path') and e.error.is_path():
                error_msg += f"\n  - Path Error: {e.error.get_path()}"
            elif hasattr(e.error, 'is_too_many_write_operations') and e.error.is_too_many_write_operations():
                error_msg += "\n  - Type: Rate Limit (Too many write operations)"
    except Exception as formatting_err:
        error_msg += f" (Note: Error while formatting detailed error: {formatting_err})"
        
    return error_msg

def log_exception(logger, message, exc=None):
    """Helper to log an exception with full context."""
    if exc:
        logger.error(f"{message}: {str(exc)}")
        logger.debug(traceback.format_exc())
    else:
        logger.exception(message)

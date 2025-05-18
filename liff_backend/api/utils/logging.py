import logging

logger = logging.getLogger(__name__)

def log_warning(source, message, user_id=None):
    log_msg = f"[{source}] {message}"
    if user_id:
        log_msg += f" (user_id={user_id})"
    logger.warning(log_msg)

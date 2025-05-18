import logging
import traceback

odoo_logger = logging.getLogger('odoo')


def log_exception(e):
    msg = f"Exception occurred: {e.__class__.__name__}: {str(e)}"
    odoo_logger.error(msg, exc_info=True)
    return msg


def log_action(api_name: str, action: str, user_id=None, extra=None):
    log_line = f"[ACTION] [{api_name}] - {action}"
    if user_id:
        log_line += f" by user_id={user_id}"
    if extra:
        log_line += f" | {extra}"
    odoo_logger.info(log_line)


def log_warning(api_name: str, reason: str, user_id=None, extra=None):
    log_line = f"[WARNING] [{api_name}] - {reason}"
    if user_id:
        log_line += f" by user_id={user_id}"
    if extra:
        log_line += f" | {extra}"
    odoo_logger.warning(log_line)

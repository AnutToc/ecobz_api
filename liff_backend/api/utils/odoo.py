import os
import requests
import logging
odoo_logger = logging.getLogger('odoo')

def odoo_rpc_call(session_id, model, method, args, call_id=1):
    url = f"{os.getenv('ODOO_URL')}/web/dataset/call_kw"
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": model,
            "method": method,
            "args": args,
            "kwargs": {},
        },
        "id": call_id
    }
    headers = {'Content-Type': 'application/json'}
    cookies = {'session_id': session_id}
    return requests.post(url, json=payload, headers=headers, cookies=cookies).json()

def log_odoo_session_usage(user_id, session_id, action):
    log_msg = f"[ODOO] User {user_id} using session '{session_id}' for action: {action}"
    print(log_msg)
    odoo_logger.info(log_msg)

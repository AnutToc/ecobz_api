from api.models import AllowedOrigin
from api.utils.logging import log_warning

def is_host_allowed(request, token_record, uid=None):
    host = request.get_host().lower()

    allowed_hosts = [
        origin.origin.replace("http://", "").replace("https://", "")
        for origin in AllowedOrigin.objects.filter(token=token_record)
    ]

    if host not in allowed_hosts:
        if uid:
            log_warning("host_check", f"Denied host: {host}", user_id=uid)
        return False
    return True

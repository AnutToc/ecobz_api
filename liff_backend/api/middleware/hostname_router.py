from django.utils.deprecation import MiddlewareMixin
from api.models import AllowedOrigin, OdooJWTToken

class HostnameProjectRouterMiddleware(MiddlewareMixin):
    def process_request(self, request):
        host = request.get_host().lower()
        request.project_denied = True

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            access_token = auth_header.split(" ")[1]
            token = OdooJWTToken.objects.filter(access_token=access_token).first()
            if token:
                allowed_hosts = [
                    origin.origin.replace("http://", "").replace("https://", "")
                    for origin in AllowedOrigin.objects.filter(token=token)
                ]
                if host in allowed_hosts:
                    request.project_denied = False

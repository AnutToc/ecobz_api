from rest_framework.permissions import BasePermission
from rest_framework_simplejwt.authentication import JWTAuthentication
from api.models import OdooJWTToken, AllowedEndpoint

class IsEndpointAllowed(BasePermission):
    def has_permission(self, request, view):
        try:
            jwt = JWTAuthentication()
            user_auth = jwt.authenticate(request)
            if not user_auth:
                return False

            user, validated_token = user_auth
            token_str = str(validated_token)

            token = OdooJWTToken.objects.filter(access_token=token_str).first()
            if not token:
                return False

            path = request.path.rstrip('/')

            allowed_paths = AllowedEndpoint.objects.filter(token=token).values_list('path', flat=True)

            for allowed_path in allowed_paths:
                allowed_path = allowed_path.rstrip('/')
                if path == allowed_path or path.startswith(allowed_path + '/'):
                    return True

            return False

        except Exception as e:
            print("Permission check error:", e)
            return False

from django.urls import path
from .token import setup_token_permissions, update_permission_scope, rotate_token, test_jwt


urlpatterns = [
    path("token/permissions/", setup_token_permissions),
    path("token/update-permission/", update_permission_scope),
    path("token/rotate/", rotate_token),
    path('test_jwt/', test_jwt, name='test_jwt')
]

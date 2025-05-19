# from django.urls import path
# from .views import *
# from .views_auto import AutoResolverAPI

# # from rest_framework_simplejwt.views import (
# #     TokenRefreshView,
# # )

# urlpatterns = [
#     path(
#         'v1/auto/<str:channel>/<str:module>/<str:action>/',
#         AutoResolverAPI.as_view(),
#         name='auto-resolver'
#     ),
#     path(
#         'v1/auto/<str:channel>/<str:module>/<str:action>/<int:res_id>/',
#         AutoResolverAPI.as_view(),
#         name='auto-resolver-id'
#     ),
    
#     path('line/users/save/', save_user, name='save_user'),
#     path('line/users/get/', get_users, name='get_users'),
#     path('line/images/save/', save_image, name='save_image'),
    
#     path('test_jwt/', test_jwt, name='test_jwt'),
    
#     # path('token/refresh', TokenRefreshView.as_view(), name='token_refresh'),
#     path('token/rotate/', rotate_token),
#     path('token/setup-permissions/', setup_token_permissions, name='setup_token_permissions'),
    
#     path('erp/login/', odoo_login, name='odoo_login'),
#     path('erp/approve_po/', odoo_approve_po, name='odoo_approve_po'),
#     path('erp/e-learning/create/', odoo_elearning_create, name='odoo_elearning_create'),
#     path('erp/e-learning/read/', odoo_elearning_read, name='odoo_elearning_read'),
#     path('erp/e-learning/update/', odoo_elearning_update, name='odoo_elearning_update'),
#     path('erp/e-learning/delete/', odoo_elearning_delete, name='odoo_elearning_delete'),
# ]
# from django.urls import path
# from api.utils.schema_views import get_dynamic_schema_view
# from api.views.line.users import save_user, get_users
# from api.views.odoo.auth_views import odoo_login
# from api.views.odoo.token import setup_token_permissions, update_permission_scope, rotate_token
# from api.views.odoo.hr.hr_employee import (
#     odoo_elearning_create, odoo_elearning_read,
#     odoo_elearning_update, odoo_elearning_delete,
# )
# from api.views.odoo.purchase.purchase_order import odoo_approve_po
# from api.views.odoo.auto_resolver import AutoResolverAPI

# urlpatterns = [
#     path("docs/", get_dynamic_schema_view(), name="docs-by-host"),
    
#     path('line/save/', save_user),
#     path('line/users/', get_users),
    
#     path('erp/login/', odoo_login),
    
#     path('erp/token/permissions/', setup_token_permissions),
#     path('erp/token/update-permission/', update_permission_scope),
#     path('erp/token/rotate/', rotate_token),
    
#     path('erp/e-learning/create/', odoo_elearning_create),
#     path('erp/e-learning/read/', odoo_elearning_read),
#     path('erp/e-learning/update/', odoo_elearning_update),
#     path('erp/e-learning/delete/', odoo_elearning_delete),
    
#     path('erp/purchase-order/approve/', odoo_approve_po),
    
#     path('v1/auto/<str:channel>/<str:module>/<str:action>/', AutoResolverAPI.as_view()),
#     path('v1/auto/<str:channel>/<str:module>/<str:action>/<int:res_id>/', AutoResolverAPI.as_view()),
# ]

# from django.urls import path, include
# from api.utils.schema_views import get_dynamic_schema_view
# from api.views.odoo.auto_resolver import AutoResolverAPI

# urlpatterns = [
#     path("docs/", get_dynamic_schema_view, name="docs-by-host"),
#     path("v1/auto/<str:channel>/<str:module>/<str:action>/", AutoResolverAPI.as_view()),
#     path("v1/auto/<str:channel>/<str:module>/<str:action>/<int:res_id>/", AutoResolverAPI.as_view()),
#     path("erp/", include("api.views.odoo.urls")),
#     path("line/", include("api.views.line.urls")),
# ]

from django.urls import path, include
from api.utils.schema_views import get_dynamic_schema_view

urlpatterns = [
    path("", get_dynamic_schema_view, name="docs-by-host"),
    # path("docs/", get_dynamic_schema_view, name="docs-by-host"),
    # path("line/", include("api.views.line.urls")),
    # path("erp/", include("api.views.odoo.urls")),
]



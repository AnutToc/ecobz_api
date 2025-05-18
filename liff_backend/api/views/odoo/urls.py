from django.urls import path
from .auth_views import odoo_login
from .token import setup_token_permissions, update_permission_scope, rotate_token
from .hr.hr_employee import (
    odoo_elearning_create, odoo_elearning_read,
    odoo_elearning_update, odoo_elearning_delete,
)
from .purchase.purchase_order import odoo_approve_po
from .km.km_management import odoo_km_create
from api.views.odoo.auto_resolver import AutoResolverAPI

urlpatterns = [
    path("login/", odoo_login),
    path("token/permissions/", setup_token_permissions),
    path("token/update-permission/", update_permission_scope),
    path("token/rotate/", rotate_token),
    path("e-learning/create/", odoo_elearning_create),
    path("e-learning/read/", odoo_elearning_read),
    path("e-learning/update/", odoo_elearning_update),
    path("e-learning/delete/", odoo_elearning_delete),
    path("purchase-order/approve/", odoo_approve_po),
    path("km/create/", odoo_km_create),
    
    path('v1/auto/<str:channel>/<str:module>/<str:action>/', AutoResolverAPI.as_view()),
    path('v1/auto/<str:channel>/<str:module>/<str:action>/<int:res_id>/', AutoResolverAPI.as_view()),
]

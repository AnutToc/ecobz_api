from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from django.urls import include, path
from api.views.odoo import urls as odoo_urls
from api.views.line import urls as line_urls
from api.views.test import urls as test_urls

# ERP schema
schema_view_erp = get_schema_view(
    openapi.Info(title="ERP API", default_version="v1"),
    public=True,
    permission_classes=[permissions.AllowAny],
    patterns=[path("", include(odoo_urls))]
)

# LINE schema
schema_view_line = get_schema_view(
    openapi.Info(title="LINE API", default_version="v1"),
    public=True,
    permission_classes=[permissions.AllowAny],
    patterns=[path("", include(line_urls))]
)

# TEST schema
schema_view_test = get_schema_view(
    openapi.Info(title="TEST API", default_version="v1"),
    public=True,
    permission_classes=[permissions.AllowAny],
    patterns=[path("", include(test_urls))]
)

# Dynamic view resolver
def get_dynamic_schema_view(request):
    host = request.get_host().lower()
    if "line" in host:
        return schema_view_line.with_ui('swagger', cache_timeout=0)(request)
    elif "erp" in host:
        return schema_view_erp.with_ui('swagger', cache_timeout=0)(request)
    elif "test" in host:
        return schema_view_test.with_ui('swagger', cache_timeout=0)(request)
    return schema_view_erp.with_ui('swagger', cache_timeout=0)(request)

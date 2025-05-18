from django.contrib import admin
from .models import LINEUser, OdooJWTToken

admin.site.register(OdooJWTToken)

@admin.register(LINEUser)
class LINEUserAdmin(admin.ModelAdmin):
    list_display = ("user_id", "display_name", "created_at", "updated_at")

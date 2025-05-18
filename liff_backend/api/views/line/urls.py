from django.urls import path
from .users import save_user, save_image, get_users

urlpatterns = [
    path("save/user", save_user),
    path('save/image', save_image),
    path("get/user", get_users),
]

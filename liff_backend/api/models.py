from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser

class LINEUser(models.Model):
    user_id = models.CharField(max_length=255, unique=True)
    display_name = models.CharField(max_length=255)
    picture_url = models.URLField(blank=True, null=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name

class OdooJWTToken(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True)
    user_id = models.IntegerField()
    session_id = models.CharField(max_length=256)
    access_token = models.TextField()
    refresh_token = models.TextField()
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Token for user_id={self.user_id}"

class AllowedEndpoint(models.Model):
    token = models.ForeignKey(OdooJWTToken, on_delete=models.CASCADE)
    path = models.CharField(max_length=512)

    def __str__(self):
        return f"{self.token} => {self.path}"

class AllowedOrigin(models.Model):
    token = models.ForeignKey(OdooJWTToken, on_delete=models.CASCADE, related_name='origins')
    origin = models.CharField(max_length=256)

    def __str__(self):
        return self.origin

class PermissionScope(models.Model):
    token = models.ForeignKey(OdooJWTToken, on_delete=models.CASCADE)
    model_name = models.CharField(max_length=255)
    can_create = models.BooleanField(default=False)
    can_read = models.BooleanField(default=False)
    can_update = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    can_approve = models.BooleanField(default=False)
    can_reject = models.BooleanField(default=False)

    class Meta:
        unique_together = ('token', 'model_name')



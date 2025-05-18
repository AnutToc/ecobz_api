from rest_framework import serializers

class TokenPermissionSetupSerializer(serializers.Serializer):
    token_id = serializers.IntegerField()
    allowed_origins = serializers.ListField(
        child=serializers.URLField(), required=False
    )
    allowed_endpoints = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    permission_scopes = serializers.ListField(
        child=serializers.DictField(), required=False
    )
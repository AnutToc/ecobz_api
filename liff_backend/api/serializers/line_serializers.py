from rest_framework import serializers
from api.models import LINEUser

class LINEUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = LINEUser
        fields = '__all__'
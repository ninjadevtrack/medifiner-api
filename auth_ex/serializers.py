from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import User


class SignInSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    # TODO: Organization and role

    class Meta:
        model = User
        fields = ('email', 'password',)

    def validate_password(self, password):
        user = self.context['request'].user
        validate_password(password, user=user)
        return password

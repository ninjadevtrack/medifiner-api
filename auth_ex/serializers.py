from django.contrib.auth.password_validation import validate_password
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from .models import User


class SignInSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('email', 'password', 'organization', 'role',)

    def validate_password(self, password):
        user = self.context['request'].user
        validate_password(password, user=user)
        return password

    def validate_role(self, role):
        if not role:
            raise serializers.ValidationError(
                _('This field may not be blank.')
            )
        return role

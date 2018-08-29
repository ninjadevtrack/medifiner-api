from __future__ import unicode_literals

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.utils.translation import ugettext_lazy as _

from .models import User


class UserCreationForm(UserCreationForm):
    """Adds email as a field in User creation."""

    class Meta:
        model = User
        fields = ('email', 'state', 'permission_level')

    def clean(self):
        state = self.cleaned_data.get('state')
        permission_level = self.cleaned_data.get('permission_level')
        if permission_level == User.STATE_LEVEL and not state:
            raise forms.ValidationError(
                {
                    'state':
                    _('You have to set a state for that permission level'),
                }
            )
        return self.cleaned_data


class UserChangeForm(UserChangeForm):
    """Uses the original change form. Change it as you wish to customize it."""

    pass


class UserAuthenticationForm(forms.Form):
    """Uses email instead of username for authentication."""

    email = forms.EmailField(label=_('Email'))
    password = forms.CharField(label=_("Password"), widget=forms.PasswordInput)

    error_messages = {
        'invalid_login': _("Please enter a correct %(email)s and password. "
                           "Note that both fields may be case-sensitive."),
        'inactive': _("This account is inactive."),
    }

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')

        if email and password:
            self.user_cache = authenticate(email=email,
                                           password=password)
            if self.user_cache is None:
                raise forms.ValidationError(
                    self.error_messages['invalid_login'],
                    code='invalid_login',
                    params={'email': 'email'},
                )
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data

    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise forms.ValidationError(
                self.error_messages['inactive'],
                code='inactive',
            )

    def get_user_id(self):
        if self.user_cache:
            return self.user_cache.id
        return None

    def get_user(self):
        return self.user_cache

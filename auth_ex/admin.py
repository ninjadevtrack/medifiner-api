from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _
from django.urls import reverse

from activity_log.admin import LogAdmin
from activity_log.models import ActivityLog

from rest_framework_jwt.serializers import (
    jwt_encode_handler,
)

from .forms import UserChangeForm, UserCreationForm
from .models import User
from .utils import jwt_payload_handler


frontend_activation_account_url = '{}/account-setup'.format(
    settings.FRONTEND_URL,
)


def send_activation_mail(modeladmin, request, queryset):
    for user in queryset:
        payload = jwt_payload_handler(user)
        token = jwt_encode_handler(payload)
        link = '{}/{}'.format(
            frontend_activation_account_url,
            token,
        )
        msg_plain = render_to_string(
            'auth_ex/emails/activation_email.txt',
            {'link': link},
        )
        msg_html = render_to_string(
            'auth_ex/emails/activation_email.html',
            {'link': link},
        )
        send_mail(
            'MedFinder Account Activation',
            msg_plain,
            settings.FROM_EMAIL,
            [user.email],
            html_message=msg_html,
        )
    queryset.update(invitation_mail_sent=True)


class UserAdmin(UserAdmin):
    """Uses the custom User model as well as the custom user creation form."""

    add_form_template = 'auth_ex/user/add_form.html'
    readonly_fields = ('invitation_mail_sent', 'organization_link')
    fieldsets = (
        (None, {'fields': (
            'email', 'password', 'invitation_mail_sent',
        )}),
        (_('Personal info'), {'fields': (
            'first_name',
            'last_name',
            'organization_link',
            'role',
            'state',
        )}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'permission_level',)}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email',
                'password1',
                'password2',
                'state',
                'permission_level',
            ),
        }),
    )
    form = UserChangeForm
    add_form = UserCreationForm
    list_display = (
        'email',
        'first_name',
        'last_name',
        'state',
        'organization_link',
        'is_staff',
        'invitation_mail_sent',
    )
    list_filter = (
        'invitation_mail_sent',
        'is_staff',
        'is_superuser',
        'is_active',
    )
    search_fields = ('first_name', 'last_name', 'email')
    ordering = ('email',)

    def organization_link(self, obj):
        if obj.organization:
            link = reverse(
                'admin:medications_organization_change',
                args=[obj.organization.id],
            )
            return format_html(
                '<a href="{link}">{text}</a>',
                link=link,
                text=obj.organization,
            )
        return None

    organization_link.short_description = _('Organization')

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions['send_activation_mail'] = (
            send_activation_mail,
            'send_activation_mail',
            _('Send activation mail')
        )
        return actions

    def get_queryset(self, request):
        return super().get_queryset(
            request
        ).select_related(
            'organization',
        )


class CustomLogAdmin(LogAdmin):
    # Crete custom adming for Logs in order to avoid creating and updating logs

    def has_add_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        if obj:
            self.readonly_fields = [
                field.name for field in obj.__class__._meta.fields
            ]
        return self.readonly_fields


admin.site.register(User, UserAdmin)
admin.site.unregister(ActivityLog)
admin.site.register(ActivityLog, CustomLogAdmin)

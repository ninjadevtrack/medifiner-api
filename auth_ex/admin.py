from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from activity_log.admin import LogAdmin
from activity_log.models import ActivityLog

from .forms import UserChangeForm, UserCreationForm
from .models import User

# TODO: for now using the api url, to be changed once it is done
frontend_activation_account_url = '{FRONTEND_DOMAIN}/register/'
frontend_activation_account_url = 'localhost:8000/api/v1/sign_in/'


def send_activation_mail(modeladmin, request, queryset):
    for user in queryset:
        if not user.invitation_mail_sent:
            link = '{}?secret={}'.format(
                frontend_activation_account_url,
                user.secret,
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
    readonly_fields = ('invitation_mail_sent', )
    fieldsets = (
        (None, {'fields': (
            'email', 'password', 'invitation_mail_sent',
        )}),
        (_('Personal info'), {'fields': ('first_name', 'last_name')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'permission_level',)}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )
    form = UserChangeForm
    add_form = UserCreationForm
    list_display = (
        'email',
        'first_name',
        'last_name',
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

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions['send_activation_mail'] = (
            send_activation_mail,
            'send_activation_mail',
            _('Send activation mail')
        )
        return actions


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

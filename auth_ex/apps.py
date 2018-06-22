from django.apps import AppConfig
from django.contrib.auth.checks import check_user_model
from django.contrib.auth.management import create_permissions
from django.core import checks
from django.db.models.signals import post_migrate
from django.utils.translation import ugettext_lazy as _


class AuthExConfig(AppConfig):
    name = 'auth_ex'
    verbose_name = _("Authentication and Authorization")

    def ready(self):
        post_migrate.connect(
            create_permissions,
            dispatch_uid="django.contrib.auth.management.create_permissions")
        checks.register(check_user_model, checks.Tags.models)

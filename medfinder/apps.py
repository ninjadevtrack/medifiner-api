from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class MedfinderConfig(AppConfig):
    name = 'medfinder'
    verbose_name = _('Medfinder')

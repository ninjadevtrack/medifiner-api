from django.apps import AppConfig


class MedicationsConfig(AppConfig):
    name = 'medications'

    def ready(self):
        from . import signals  # noqa

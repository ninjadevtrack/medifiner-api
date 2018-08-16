import os
import raven

from celery import Celery
from raven.contrib.celery import register_signal, register_logger_signal


class Celery(Celery):

    def on_configure(self):
        client = raven.Client(
        	'https://e538805d79de4617925990bf8968a662:7a48ee6019ff4feeb5177e9ee04080cb@sentry.io/1241649' # noqa
        )

        # register a custom filter to filter out duplicate logs
        register_logger_signal(client)

        # hook into the Celery error handler
        register_signal(client)


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medfinder.settings.default')

app = Celery('medfinder')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

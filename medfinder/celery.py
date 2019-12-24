import os
import raven

from celery import Celery
from raven.contrib.celery import register_signal, register_logger_signal


class Celery(Celery):

    def on_configure(self):
        client = raven.Client(
                'https://cea486b768ce40f4908c2814f06763f0:702d98f0d3e54e099fda62ff73ab6662@sentry.io/1314513'  # noqa
        )

        # register a custom filter to filter out duplicate logs
        register_logger_signal(client)

        # hook into the Celery error handler
        register_signal(client)


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medfinder.settings.default')

app = Celery('medfinder')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

import os
from celery import Celery


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medfinder.settings.default')

app = Celery('medfinder')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

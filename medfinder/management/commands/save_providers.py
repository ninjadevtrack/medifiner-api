import time
from datetime import datetime

from django.core.management.base import BaseCommand

from medications.models import Provider


class Command(BaseCommand):
    """
    Run Task state_cache_provier_count
    """
    help = 'Run Task state_cache_provier_count'

    def handle(self, *args, **options):
        for provider in Provider.objects.all():
            provider.save()

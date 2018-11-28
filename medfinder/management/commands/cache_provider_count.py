import time
from datetime import datetime

from django.core.management.base import BaseCommand

from medications import tasks


class Command(BaseCommand):
    """
    Run Task state_cache_provier_count
    """
    help = 'Run Task state_cache_provier_count'

    def handle(self, *args, **options):
        tasks.state_cache_provider_count()
        tasks.county_cache_provider_count()
        tasks.zipcode_cache_provider_count()

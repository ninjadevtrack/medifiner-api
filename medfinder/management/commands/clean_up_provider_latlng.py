import time
from datetime import datetime

from django.core.management.base import BaseCommand

from medications.models import Provider
from django.contrib.gis.geos import Point


# docker-compose -f dev.yml run django python manage.py clean_up_provider_latlng
class Command(BaseCommand):
    """
    Import from Vaccine Finder DB to populate provider type
    """
    help = 'Import from Vaccine Finder DB to provider type'

    def handle(self, *args, **options):
        self.clean_up_provider_latlng()

    def clean_up_provider_latlng(self):
        providers = Provider.objects.all()
        for provider in providers:
            if provider.lat and provider.lng:
                provider.geo_localization = Point(
                    float(provider.lng),
                    float(provider.lat),
                )
                provider.save()

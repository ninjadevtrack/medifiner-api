import json

from django.core.management.base import BaseCommand

from django.contrib.gis.db.models.functions import Centroid, AsGeoJSON
from medications.models import State


class Command(BaseCommand):
    """
    Run Task state_cache_provier_count
    """
    help = 'Run Task state_cache_provier_count'

    def handle(self, *args, **options):
        states = State.objects.all().annotate(
            centroid=AsGeoJSON(Centroid('geometry')),
        )

        for state in states:
            center_data = json.loads(state.centroid)
            lng = center_data['coordinates'][0]
            lat = center_data['coordinates'][1]
            state.center_lng = lng
            state.center_lat = lat
            state.save()

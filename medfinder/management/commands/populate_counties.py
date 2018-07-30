import json
import requests

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry

from medications.models import County, State


class Command(BaseCommand):
    """
    Import counties with geometry from external database
    """
    help = 'Populate db with counties data'

    def handle(self, *args, **options):
        if County.objects.all().count() > 3220:
            raise CommandError('Counties already imported')
        if not State.objects.exists():
            raise CommandError('You must generate states first.')
        database_json = settings.US_COUNTIES_DATABASE
        response = requests.get(database_json)
        json_response = response.json()
        for feature in json_response['features']:
            state_id = feature['properties']['STATE']
            county_name = feature['properties']['NAME']
            print('Importing county {}'.format(county_name))
            county_geometry = GEOSGeometry(json.dumps(feature['geometry']))
            state = State.objects.get(state_us_id=state_id)
            County.objects.create(
                county_name=county_name,
                geometry=county_geometry,
                state=state,
            )

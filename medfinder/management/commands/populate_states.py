import json
import requests

from django.core.management.base import BaseCommand
from django.contrib.gis.geos import GEOSGeometry
from django.conf import settings
from localflavor.us.us_states import USPS_CHOICES

from medications.models import State


class Command(BaseCommand):
    """
    Import states with geometry from external database
    """
    help = 'Populate db with states data'

    def handle(self, *args, **options):
        database_json = settings.US_STATES_DATABASE
        dict_states = dict((v, k) for k, v in dict(USPS_CHOICES).items())
        response = requests.get(database_json)
        json_response = response.json()
        for feature in json_response['features']:
            state_us_id = feature['id']
            state_name = feature['properties']['name']
            state_geometry = GEOSGeometry(json.dumps(feature['geometry']))
            state_code = dict_states.get(state_name)
            if state_name.lower() == 'district of columbia':
                state_name = 'Washington D.C.'
            State.objects.get_or_create(
                state_code=state_code,
                state_name=state_name,
                geometry=state_geometry,
                state_us_id=state_us_id,
            )

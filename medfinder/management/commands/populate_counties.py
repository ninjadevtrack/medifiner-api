import json
import requests

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry
from django.utils.text import slugify

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
            county_id = feature['properties']['COUNTY']
            geo_id = feature['properties']['GEO_ID'].split('US')[1]
            print('Importing county {}'.format(county_name))
            county_geometry = GEOSGeometry(json.dumps(feature['geometry']))
            state = State.objects.get(state_us_id=state_id)
            # We have to handle somehow the case of baltimore, database
            # gives the same name for baltimore-county and baltimore-city
            # the first one imported is baltimore county so we have to hardcode
            # that the second time it finds baltimore, change it to
            # baltimore city. This is a temporary solution until we find
            # anothe more elegant workaround. TODO.
            if county_name.lower() == 'baltimore':
                if County.objects.filter(
                    county_name_slug='baltimore',
                ).exists():
                    county_name = 'Baltimore City'
            County.objects.create(
                county_name=county_name,
                county_name_slug=slugify(county_name),
                geometry=county_geometry,
                state=state,
                county_id=county_id,
                geo_id=geo_id,
            )

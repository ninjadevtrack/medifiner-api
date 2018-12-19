import requests

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry
from json import JSONDecodeError, dumps

from medications.models import State, ZipCode


class Command(BaseCommand):
    """
    Import zipcodes with geometry from external database
    """
    help = 'Populate db with zipcodes data'

    def handle(self, *args, **options):
        states = State.objects.all()
        if not states:
            raise CommandError(
                'Please import states before running this task.')
        if ZipCode.objects.all().count() > 33000:
            raise CommandError('ZipCodes already imported.')
        for state in states:
            if state.state_code == 'PR':
                continue
            print('Getting zipcodes for {}'.format(state))
            if 'D.C.' in state.state_name:
                state_url = settings.US_ZIPCODES_DATABASE.format(
                    'dc',
                    'district_of_columbia',
                )

            else:
                state_url = settings.US_ZIPCODES_DATABASE.format(
                    state.state_code.lower(),
                    state.state_name.lower().replace(' ', '_'),
                )

            try:
                state_response_json = requests.get(state_url).json()
                for zipcode_json in state_response_json['features']:
                    zipcode = zipcode_json['properties']['ZCTA5CE10']
                    geometry = GEOSGeometry(dumps(zipcode_json['geometry']))
                    ZipCode.objects.create(
                        geometry=geometry,
                        zipcode=zipcode,
                        state=state,
                    )
            except JSONDecodeError:
                # Catch if the state is not in the zipcode database
                print('No zipcodes for this state in the database')
                pass

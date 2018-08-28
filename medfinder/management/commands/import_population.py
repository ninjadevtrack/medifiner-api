import requests

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from medications.models import County, State, ZipCode


URL_CENSUS = 'https://api.census.gov/data/2010/sf1'
POPULATION_VARIABLE = 'P0010001'

REQUEST_STATE = '?get={population_variable}&for=state:{state_id}&key={api_key}' # noqa
REQUEST_COUNTY = '?get={population_variable}&for=county:{county_id}&in=state:{state_id}&key={api_key}' # noqa
REQUEST_ZIPCODE = '?get={population_variable}&for=zip%20code%20tabulation%20area:{zipcode}&in=state:{state_id}&key={api_key}' # noqa


class Command(BaseCommand):
    """
    Import population for every level of geopraphy
    """
    help = 'Populate db population for all geographies'

    def handle(self, *args, **options):
        states = State.objects.all()
        counties = County.objects.exists()
        zipcodes = ZipCode.objects.exists()
        if not states or not counties or not zipcodes:
            raise CommandError(
                'You must generate states, counties and zipcodes first.',
            )
        for state in states:
            # Generate request for the current state
            print(
                'Requesting population for counties '
                'and zipcodes in {}.'.format(state)
            )
            request_for_state = REQUEST_STATE.format(
                population_variable=POPULATION_VARIABLE,
                state_id=state.state_us_id,
                api_key=settings.CENSUS_API_KEY,
            )
            full_path_request_for_state = URL_CENSUS + request_for_state
            response = requests.get(full_path_request_for_state)
            data_response = response.json()
            try:
                population = int(data_response[1][0])
                state.population = population
                state.save()
            except ValueError:
                pass
            print('Requesting population for county:')
            for county in state.counties.all():
                print(county)
                # Generate request for the current state counties
                request_for_county = REQUEST_COUNTY.format(
                    population_variable=POPULATION_VARIABLE,
                    county_id=county.county_id,
                    state_id=state.state_us_id,
                    api_key=settings.CENSUS_API_KEY,
                )
                full_path_request_for_county = URL_CENSUS + request_for_county
                response = requests.get(full_path_request_for_county)
                data_response = response.json()
                try:
                    population = int(data_response[1][0])
                    county.population = population
                    county.save()
                except ValueError:
                    pass
            print('Requesting population for zipcode:')
            for zipcode in state.state_zipcodes.all():
                print(zipcode.zipcode)
                # Generate request for the current state zipcodes
                request_for_zipcode = REQUEST_ZIPCODE.format(
                    population_variable=POPULATION_VARIABLE,
                    zipcode=zipcode.zipcode,
                    state_id=state.state_us_id,
                    api_key=settings.CENSUS_API_KEY,
                )
                full_path_request_for_zipcode = URL_CENSUS + request_for_zipcode # noqa
                response = requests.get(full_path_request_for_zipcode)
                data_response = response.json()
                try:
                    population = int(data_response[1][0])
                    zipcode.population = population
                    zipcode.save()
                except ValueError:
                    pass
            print('Imported all populations succesfully!')

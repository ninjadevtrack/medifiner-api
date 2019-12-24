import requests

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from medications.models import County, State, ZipCode

URL_CENSUS = 'https://api.census.gov/data/2017/pep/population'
URL_CENSUS_2010 = 'https://api.census.gov/data/2010/sf1'
POPULATION_VARIABLE = 'POP'
POPULATION_VARIABLE_2010 = 'P0010001'

REQUEST_STATE = '?get={population_variable}&for=state:{state_id}&key={api_key}' # noqa
REQUEST_COUNTY = '?get={population_variable}&for=county:*&in=state:{state_id}&key={api_key}' # noqa
SPECIAL_REQUEST_COUNTY = '?get={population_variable}&for=county:{county_id}&in=state:{state_id}&key={api_key}' # noqa
REQUEST_ZIPCODE = '?get={population_variable}&for=zip%20code%20tabulation%20area:*&in=state:{state_id}&key={api_key}' # noqa


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
            state_data_response = response.json()
            try:
                population = int(state_data_response[1][0])
                state.population = population
                state.save()
            except ValueError:
                pass

            # Generate request all counties in this state
            request_for_county = REQUEST_COUNTY.format(
                population_variable=POPULATION_VARIABLE,
                state_id=state.state_us_id,
                api_key=settings.CENSUS_API_KEY,
            )
            full_path_request_for_county = URL_CENSUS + request_for_county
            response = requests.get(full_path_request_for_county)
            county_data_response = response.json()

            # Create a python dict with 'county_id: population' values
            # so we dont have to ask again to the API for every county
            county_pop_map = {
                data[2]: data[0] for data in county_data_response
            }

            for county in state.counties.all():
                print('Fething population for: {}'.format(county))
                # Save the population for every county looking at the
                # county_pop_map

                county_id = f'{county.county_id:03}' # noqa
                try:
                    population = int(county_pop_map.get(county_id))
                except TypeError:
                    # the 2017 has no data for some counties, in that case we
                    # ask to the 2010 census for this special county
                    print(
                        'No data for {}, requesting data from the'
                        ' 2010 census'.format(county)
                    )
                    request_for_county = SPECIAL_REQUEST_COUNTY.format(
                        population_variable=POPULATION_VARIABLE_2010,
                        county_id=county.county_id,
                        state_id=state.state_us_id,
                        api_key=settings.CENSUS_API_KEY,
                    )
                    full_path_request_for_county = \
                        URL_CENSUS_2010 + request_for_county
                    response = requests.get(full_path_request_for_county)
                    county_data_response = response.json()
                    population = int(county_data_response[1][0])
                county.population = population
                county.save()

            request_for_zipcode = REQUEST_ZIPCODE.format(
                population_variable=POPULATION_VARIABLE_2010,
                state_id=state.state_us_id,
                api_key=settings.CENSUS_API_KEY,
            )
            full_path_request_for_zipcode = URL_CENSUS_2010 + request_for_zipcode # noqa
            response = requests.get(full_path_request_for_zipcode)
            zipcode_data_response = response.json()

            # # Create a python dict with 'zipcode: population' values
            # # so we dont have to ask again to the API for every zipcode
            zipcode_pop_map = {
                data[2]: data[0] for data in zipcode_data_response
            }

            for zipcode in state.state_zipcodes.all():
                print('Fething population for: {}'.format(zipcode))
                # Save the population for every county looking at the
                # county_pop_map
                population = int(zipcode_pop_map.get(zipcode.zipcode))
                zipcode.population = population
                zipcode.save()

            print('Imported all populations for {} succesfully!'.format(state))
        print('IMPORTED ALL POPULATIONS SUCCESFULLY!')

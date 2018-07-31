import json
import requests

from django.db.models import Q
from django.core.exceptions import MultipleObjectsReturned
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from medications.models import County, State, ZipCode


class Command(BaseCommand):
    """
    Import a json used to relate counties to zipcodes
    """
    help = 'Relate counties to zipcodes'

    def handle(self, *args, **options):
        if not County.objects.exists():
            raise CommandError('You must generate counties first.')
        if not State.objects.exists():
            raise CommandError('You must generate states first.')
        if not ZipCode.objects.exists():
            raise CommandError('You must generate zipcodes first.')

        # county_check = []
        # # The url accepts the status code, so we just have to change it while
        # # iterating per state codes
        # base_url = 'http://gomashup.com/json.php?fds=geo/usa/zipcode/state/{}'

        # for state in State.objects.only('state_code', 'state_name'):
        #     url = base_url.format(state.state_code)
        #     print('Relate zipcodes to counties in {}'.format(state.state_name))
        #     response = requests.get(url)
        #     # Since the json that we get has ( and ) at the beggining and end
        #     # we have to replace then by '' in order to load the json properly
        #     content = response.text
        #     content = content.replace('(', '')
        #     content = content.replace(')', '')
        #     response_json = json.loads(content)
        #     for result in response_json['result']:
        #         zipcode = result.get('Zipcode')
        #         county_name = result.get('County')
        #         county_name_slug = slugify(
        #             result.get('County').replace('SAINT', 'st.')
        #         )
        #         county_name_no_space = result.get(
        #             'County').replace('SAINT', 'st.').replace(' ', '')
        #         if county_name_slug in county_check or county_name in county_check:
        #             continue
        #         try:
        #             county = County.objects.get(
        #                 county_name_slug__iexact=county_name_slug,
        #                 state__state_code=state.state_code,
        #             )

        #         except County.DoesNotExist:
        #             try:
        #                 county = County.objects.get(
        #                     county_name__iexact=county_name_no_space.lower(),
        #                     state__state_code=state.state_code,
        #                 )
        #             except County.DoesNotExist:
        #                 county = County.objects.get(
        #                     county_name__icontains=county_name.lower(),
        #                     state__state_code=state.state_code,
        #                 )
        #         except MultipleObjectsReturned:
        #             print('2 objects for {}'.format(county_name))

        #         county_check = [county_name, county_name_slug]

        #         try:
        #             zipcode_obj = ZipCode.objects.get(
        #                 zipcode=zipcode,
        #                 state__state_code=state.state_code,
        #             )
        #         except ZipCode.DoesNotExist:
        #             # print('Zipcode {} not found, ommitting'.format(zipcode))
        #             pass
        #         except MultipleObjectsReturned:
        #             print(zipcode)
        #             raise CommandError(
        #                 'ERROR, zipcodes should be unique for state',
        #             )
        #         if county and zipcode_obj:
        #             zipcode_obj.county = county
        #             zipcode_obj.save()

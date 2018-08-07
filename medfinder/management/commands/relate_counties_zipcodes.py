import csv
import requests

from django.core.exceptions import MultipleObjectsReturned
from django.core.management.base import BaseCommand, CommandError

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

        not_related = []

        base_url = 'https://www2.census.gov/geo/docs/maps-data/data/rel/zcta_county_rel_10.txt'
        response = requests.get(base_url)
        reader = csv.DictReader(response.text.split('\n'))
        print(
            'Relating all US zipcodes to their related counties,'
            ' this may take a while...'
        )
        for row in reader:
            county = None
            zip_obj = None
            county_id = row.get('COUNTY')
            geo_id = row.get('GEOID')
            state = row.get('STATE')
            if state == '72':
                # Skip Puerto Rico since we dont have zipcodes for it
                continue
            try:
                county = County.objects.get(
                    county_id=county_id,
                    geo_id=geo_id,
                    state__state_us_id=state,
                )
            except County.DoesNotExist:
                print(
                    'Could not find county for id {} and geo id {}'.format(
                        county_id,
                        geo_id,
                    )
                )
            except MultipleObjectsReturned:
                # In very few cases the counties database gave us a duplicated
                # counties for the same state, so in that case we just take the
                # first since they are the same county.
                county = County.objects.filter(
                    county_id=county_id,
                    geo_id=geo_id,
                    state__state_us_id=state,
                ).first()

            zipcode = row.get('ZCTA5')
            try:
                zip_obj = ZipCode.objects.get(
                    zipcode=zipcode,
                    state__state_us_id=state,
                )
            except ZipCode.DoesNotExist:
                print(
                    'Could not find zipcode {}'.format(
                        zipcode,
                    )
                )
            except MultipleObjectsReturned:
                print(zipcode)

            if county and zip_obj:
                zip_obj.counties.add(county)
            else:
                not_related.append((county, zip_obj))
        print(
            'List of (county, zipcode) that were not related: {}'.format(
                not_related,
            )
        )


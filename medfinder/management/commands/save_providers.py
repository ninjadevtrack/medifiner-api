import time
from datetime import datetime

from django.core.management.base import BaseCommand

from medications.models import Provider, State


class Command(BaseCommand):
    """
    Run Task state_cache_provier_count
    """
    help = 'Run Task state_cache_provier_count'

    def handle(self, *args, **options):
        providers = Provider.objects.filter(related_state_id__isnull=True)

        for provider in providers:
            if provider.related_zipcode_id:
                provider.related_state_id = provider.related_zipcode.state_id

                if not provider.related_county_id:
                    county_ids = []
                    for county in provider.related_zipcode.counties.all():
                        county_ids.append(county.id)

                    if len(county_ids) > 0:
                        provider.related_county_id = county_ids[0]

                provider.save()
            else:
                states = State.objects.filter(state_code=provider.state)
                if len(states) > 0:
                    provider.related_state_id = states[0].id
                    provider.save()

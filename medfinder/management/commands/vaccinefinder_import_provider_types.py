import time
from datetime import datetime

from django.core.management.base import BaseCommand

from medications.models import Organization, Provider, ProviderType
from vaccinefinder.models import VFOrganization, VFProvider


# docker-compose -f dev.yml run django python manage.py vaccinefinder_import
class Command(BaseCommand):
    """
    Import from Vaccine Finder DB to populate provider type
    """
    help = 'Import from Vaccine Finder DB to provider type'

    def handle(self, *args, **options):
        self.pull_in_provider_types()

    def find_provider_type(self, vaccinefinder_type_id):
        type = self.vaccine_finder_type_map(vaccinefinder_type_id)
        if type:
            provider_type, created = ProviderType.objects.get_or_create(
                name=type)
            return provider_type
        else:
            return None

    def vaccine_finder_type_map(self, vaccinefinder_type_id):
        types = {
            1: "Clinic",
            2: "Health Department",
            3: "Healthcare Provider’s Office",
            4: "Pharmacy",
            5: "Community Provider / Immunizer",
            6: "Tribal Health Center",
        }
        return types[vaccinefinder_type_id] if vaccinefinder_type_id != 0 else None

    def pull_in_provider_types(self):
        provider_type, created = ProviderType.objects.get_or_create(
            code='CO',
            name='Commercial',
        )

        already_processed_vaccine_finder_ids = Provider.objects.filter(
            vaccine_finder_type__isnull=False).values_list('vaccine_finder_id', flat=True)

        already_processed_vaccine_finder_ids = set(
            list(already_processed_vaccine_finder_ids))

        vf_provider_ids_and_types = VFProvider.objects.using(
            'vaccinedb').exclude(provider_id__in=already_processed_vaccine_finder_ids).values('provider_id', 'type')

        for vf_provider_id_and_type in vf_provider_ids_and_types:
            providers = Provider.objects.filter(
                vaccine_finder_id=vf_provider_id_and_type['provider_id'])

            if len(providers) == 1:
                provider = providers[0]
                provider.type = (provider_type if vf_provider_id_and_type['type'] == 4 else self.find_provider_type(
                    vf_provider_id_and_type['type']))
                provider.vaccine_finder_type = vf_provider_id_and_type['type']
                provider.save()

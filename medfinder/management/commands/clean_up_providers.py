from datetime import datetime

from django.core.management.base import BaseCommand

from medications.models import Provider, ProviderMedicationNdcThrough


class Command(BaseCommand):
    """
    Import from Vaccine Finder DB to populate provider type
    """
    help = 'Import from Vaccine Finder DB to provider type'

    def handle(self, *args, **options):
        for provider in Provider.objects.exclude(name='').all():
            providers_to_delete = Provider.objects.filter(
                name='', store_number=provider.store_number)
            if len(providers_to_delete) == 1:
                provider_to_delete = providers_to_delete[0]
                provider.related_zipcode_id = provider_to_delete.related_zipcode_id
                provider.save()

                ProviderMedicationNdcThrough.objects.filter(
                    provider_id=provider_to_delete.pk).update(provider_id=provider.pk)

                provider_to_delete.delete()
            elif len(providers_to_delete) > 1:
                print("WILL NOT PROCESS PROVIDER ID")
                print(provider.pk)

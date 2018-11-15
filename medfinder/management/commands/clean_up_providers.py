from datetime import datetime

from django.core.management.base import BaseCommand
from django.db.models import Count

from medications.models import Provider, ProviderMedicationNdcThrough


class Command(BaseCommand):
    """
    Import from Vaccine Finder DB to populate provider type
    """
    help = 'Import from Vaccine Finder DB to provider type'

    def handle(self, *args, **options):
        self.delete_duplicates()

    def delete_duplicates(self):
        walgreens_id = 5

        store_numbers = Provider.objects.filter(organization_id=walgreens_id).values(
            'store_number').annotate(Count('id')).order_by().filter(id__count__gt=1)

        print(store_numbers)

        for store_number_data in store_numbers:
            store_number = store_number_data['store_number']

            providers_to_delete = Provider.objects.filter(
                store_number=store_number, active=False, organization_id=walgreens_id)

            providers_to_keep = Provider.objects.filter(
                store_number=store_number, active=True, organization_id=walgreens_id)

            if providers_to_keep.count() == 1:
                provider_to_keep = providers_to_keep[0]

                if providers_to_delete.count() > 0:
                    for provider_to_delete in providers_to_delete:

                        ProviderMedicationNdcThrough.objects.filter(
                            provider_id=provider_to_delete.pk).update(provider_id=provider_to_keep.pk)

                        provider_to_delete.delete()
                print('Cleaned up')
                print(store_number)
            elif providers_to_keep.count() > 1:
                print('More than 1 active provider found for')
                print(store_number)
            else:
                print('No active provider found for')
                print(store_number)

        store_numbers = Provider.objects.filter(organization_id=walgreens_id).values(
            'store_number').annotate(Count('id')).order_by().filter(id__count__gt=1)

        print(store_numbers)

    def delete_provider_with_empty_names(self):
        for provider in Provider.objects.exclude(name='').all():
            no_name_providers = Provider.objects.filter(
                name='', store_number=provider.store_number)
            if len(no_name_providers) == 1:
                no_name_provider = no_name_providers[0]
                no_name_provider.address = provider.address
                no_name_provider.city = provider.city
                no_name_provider.email = provider.email
                no_name_provider.end_date = provider.end_date
                no_name_provider.insurance_accepted == provider.insurance_accepted
                no_name_provider.name = provider.name
                no_name_provider.notes = provider.notes
                no_name_provider.operating_hours = provider.operating_hours
                no_name_provider.phone = provider.phone
                no_name_provider.related_zipcode_id = provider.related_zipcode_id
                no_name_provider.start_date = provider.start_date
                no_name_provider.state = provider.state
                no_name_provider.store_number = provider.store_number
                no_name_provider.type_id = provider.type_id
                no_name_provider.website = provider.website
                no_name_provider.walkins_accepted = provider.walkins_accepted
                no_name_provider.zip = provider.zip
                no_name_provider.save()

            elif len(no_name_providers) > 1:
                print("WILL NOT PROCESS PROVIDER ID")
                print(provider.pk)

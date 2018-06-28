import csv

from celery import shared_task
from django.db import transaction

from .models import (
    Medication,
    Organization,
    Provider,
    ProviderMedicationThrough,
    TemporaryFile,
)


@shared_task
@transaction.atomic
def generate_medications(temporary_csv_file_id, organization_id):
    # Already checked in serializer validation that this organization exists.
    organization = Organization.objects.get(pk=organization_id)
    provider = None
    medication = None
    temporary_file_obj = TemporaryFile.objects.get(pk=temporary_csv_file_id)
    print(temporary_file_obj, temporary_file_obj.file.path)
    decoded_file = temporary_file_obj.file.read().decode('utf-8').splitlines()
    reader = csv.DictReader(decoded_file)
    for row in reader:
        # Iterate through the rows to get the neccessary information

        if provider:
            # Check if we already have a provider cached and if it is the same
            # as the next in line to avoid too much queries to the DB.
            if provider.store_number != row.get('store #'):
                provider, _ = Provider.objects.get_or_create(
                    organization=organization,
                    store_number=row.get('store #'),
                    address=row.get('address'),
                    city=row.get('city'),
                    zip=row.get('zipcode'),
                    state=row.get('state'),
                    phone=row.get('phone'),
                    change_coordinates=True,
                )
        else:
            provider, _ = Provider.objects.get_or_create(
                organization=organization,
                store_number=row.get('store #'),
                address=row.get('address'),
                city=row.get('city'),
                zip=row.get('zipcode'),
                state=row.get('state'),
                phone=row.get('phone'),
                change_coordinates=True,
            )

        if medication:
            # Will do the same check as in provider
            if medication.ndc != row.get('med_code'):
                medication, _ = Medication.objects.get_or_create(
                    name=row.get('med_name'),
                    ndc=row.get('med_code'),
                )
        else:
            medication, _ = Medication.objects.get_or_create(
                name=row.get('med_name'),
                ndc=row.get('med_code'),
            )

        if provider and medication:
            ProviderMedicationThrough.objects.update_or_create(
                provider=provider,
                medication=medication,
                supply=row.get('supply_level'),
            )
    temporary_file_obj.delete()










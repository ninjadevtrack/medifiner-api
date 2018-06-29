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
    medication_map = {}  # Use this map to save queries to the DB
    temporary_file_obj = TemporaryFile.objects.get(pk=temporary_csv_file_id)
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
                )
        else:
            # In the first row after headers we don't have any provider, so we
            # have to get it from the DB or create it
            provider, _ = Provider.objects.get_or_create(
                organization=organization,
                store_number=row.get('store #'),
                address=row.get('address'),
                city=row.get('city'),
                zip=row.get('zipcode'),
                state=row.get('state'),
                phone=row.get('phone'),
            )

        if medication:
            # Will do the same check as in provider
            if medication.ndc != row.get('med_code'):
                # Second check in the medication_map to lookup if this
                # medication has been created already from this file
                medication = medication_map.get(row.get('med_code'), None)
                if not medication:
                    medication, _ = Medication.objects.get_or_create(
                        name=row.get('med_name'),
                        ndc=row.get('med_code'),
                    )
        else:
            # In the first row after headers we don't have any medication, so
            # we have to get it from the DB or create it
            medication, _ = Medication.objects.get_or_create(
                name=row.get('med_name'),
                ndc=row.get('med_code'),
            )
        if medication:
            # Add the actual medication (whatever it is) to the medication map
            # We will use as key the ndc which is supossed to be a real life
            # id which should be unique, the value will be the object that
            # we can get. Python get from dict uses much less programmatic time
            # than a SQL get.
            medication_map[medication.ndc] = medication
            # TODO: the ndc may not be unique in cases when the same medication
            # has different weights or number of pills. To be checked
            # with the client.

        if provider and medication:
            # Create or update the relation object
            ProviderMedicationThrough.objects.update_or_create(
                provider=provider,
                medication=medication,
                supply=row.get('supply_level'),
            )

    # Make celery delete the django object that has our csv file
    temporary_file_obj.delete()

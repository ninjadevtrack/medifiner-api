import re
import csv

from io import BytesIO
from zipfile import ZipFile
from urllib.request import urlopen
from celery import shared_task
from django.db import transaction
from django.db.utils import IntegrityError
from django.conf import settings

from .models import (
    ExistingMedication,
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

        if provider and medication:
            # Create or update the relation object
            ProviderMedicationThrough.objects.update_or_create(
                provider=provider,
                medication=medication,
                supply=row.get('supply_level'),
            )

    # Make celery delete the django object that has our csv file
    temporary_file_obj.delete()


# TODO: Create celerybeat task 
# TODO: should it be atomic?
def import_existing_medications():
    # create a pattern to validate ndc's
    pattern = re.compile(
        '\d{4}-\d{4}-\d{2}|\d{5}-\d{3}-\d{2}|\d{5}-\d{4}-\d{1}|\d{5}-\*\d{3}-\d{2}'
    )
    url = urlopen(settings.NDC_DATABASE_URL)
    if not url:
        return
    zipfile = ZipFile(BytesIO(url.read()))
    if 'package.xls' in zipfile.namelist():
        # For now just assume that this is the file to use, not product.xls
        extracted_xls_file = zipfile.open('package.xls')
        all_medications = [
            line.decode('utf-8').split('\t')
            for line in extracted_xls_file.readlines()
        ]
        for medication in all_medications:
            ndc = medication[2]
            name = medication[3]
            if bool(pattern.match(ndc)):
                try:
                    ExistingMedication.objects.get_or_create(
                        ndc=ndc,
                        name=name
                    )
                except IntegrityError:
                    # During development found a duplicate ndc
                    pass

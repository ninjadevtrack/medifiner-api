import re
import csv

from io import BytesIO
from zipfile import ZipFile
from urllib.request import urlopen
from celery import shared_task
from django.db import transaction
from django.core.cache import cache
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
    existing_ndc_codes = ExistingMedication.objects.values_list(
        'ndc',
        flat=True,
    )
    provider = None
    medication = None
    medication_map = {}  # Use this map to save queries to the DB
    temporary_file_obj = TemporaryFile.objects.get(pk=temporary_csv_file_id)
    decoded_file = temporary_file_obj.file.read().decode('utf-8').splitlines()
    reader = csv.DictReader(decoded_file)
    for row in reader:
        # Iterate through the rows to get the neccessary information
        store_number = row.get('store #')
        address = row.get('address')
        city = row.get('city')
        zip_code = row.get('zipcode')
        state = row.get('state')
        phone = row.get('phone')
        ndc_code = row.get('med_code')
        med_name = row.get('med_name')

        # First check if the ndc code exists in real life, if not, don't use
        # unnecesary time in meaningless queries
        if ndc_code in existing_ndc_codes:
            if not provider or (
                provider and provider.store_number != store_number
            ):
                # Check if we already have a provider cached and if it is the
                # same as the next in line to avoid too much queries to the DB.
                provider, _ = Provider.objects.get_or_create(
                    organization=organization,
                    store_number=store_number,
                    address=address,
                    city=city,
                    zip=zip_code,
                    state=state,
                    phone=phone,
                )
            if not medication or (medication.ndc != ndc_code):
                # Will do the same check as in provider
                # Second check in the medication_map to lookup if this
                # medication has been created already from this file
                medication = medication_map.get(ndc_code, None)
                if not medication:
                    medication, _ = Medication.objects.get_or_create(
                        name=med_name,
                        ndc=ndc_code,
                    )

            if medication:
                # Add the actual medication (whatever it is) to the medication
                # map. We will use as key the ndc which is supossed to be a
                # real life id which should be unique, the value will be the
                # object that we can get. Python get from dict uses much
                # less programmatic time than a SQL get.
                medication_map[medication.ndc] = medication

            if provider and medication:
                # Create or update the relation object
                ProviderMedicationThrough.objects.create(
                    provider=provider,
                    medication=medication,
                    supply=row.get('supply_level'),
                )

    # Make celery delete the django object that has our csv file
    temporary_file_obj.delete()


@shared_task
def import_existing_medications():
    # create a pattern to validate ndc's
    pattern = re.compile(
        '\d{4}-\d{4}-\d{2}|\d{5}-\d{3}-\d{2}|\d{5}-\d{4}-\d{1}|\d{5}-\*\d{3}-\d{2}'
    )
    url = urlopen(settings.NDC_DATABASE_URL)
    cached_ndc_list = cache.get('cached_ndc_list', [])
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
            description = medication[3]
            if ndc in cached_ndc_list:
                # No need to create if ndc is in the cache
                continue
            if bool(pattern.match(ndc)):
                ExistingMedication.objects.create(
                    ndc=ndc,
                    description=description
                )
                cached_ndc_list.append(ndc)
    cache.set('cached_ndc_list', cached_ndc_list, None)

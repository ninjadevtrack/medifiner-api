import re
import csv

from celery import shared_task
from celery.decorators import task
from datetime import timedelta
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import MultipleObjectsReturned, ValidationError
from django.core.mail import send_mail
from django.db import IntegrityError
from django.utils import timezone
from io import BytesIO
from urllib.request import urlopen
from zipfile import ZipFile

from .models import (
    ExistingMedication,
    MedicationNdc,
    Organization,
    Provider,
    ProviderMedicationNdcThrough,
    ZipCode,
)


@shared_task
# This task can't be atomic because we need to run a post_save signal for
# every ProviderMedicationThrough object created
def generate_medications(cache_key, organization_id, email_to):
    # Already checked in serializer validation that this organization exists.
    lost_ndcs = []

    # A list to update the last_import_date field in
    # all providers during this import
    updated_providers = []

    organization = Organization.objects.get(pk=organization_id)
    existing_ndc_codes = ExistingMedication.objects.values_list(
        'ndc',
        flat=True,
    )
    provider = None
    medication_ndc = None
    medication_ndc_map = {}  # Use this map to save queries to the DB
    csv_file = cache.get(cache_key)
    temporary_file_obj = csv_file.open()
    decoded_file = temporary_file_obj.read().decode('utf-8').splitlines()
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
                # same as the next in line to avoid too much queries to the DB
                # and try to get the zipcode object to relate it to provider.
                try:
                    zipcode_obj = ZipCode.objects.get(zipcode=zip_code)
                except MultipleObjectsReturned:
                    zipcode_obj = ZipCode.objects.filter(zipcode=zip_code)[0]
                except ZipCode.DoesNotExist:
                    zipcode_obj = None
                # TODO: type and category? Home delivery info?
                provider, created = Provider.objects.get_or_create(
                    organization=organization,
                    store_number=store_number,
                    address=address,
                    city=city,
                    zip=zip_code,
                    state=state,
                    phone=phone,
                    related_zipcode=zipcode_obj,
                )

            if not medication_ndc or (medication_ndc.ndc != ndc_code):
                # Will do the same check as in provider
                # Second check in the medication_map to lookup if this
                # medication has been created already from this file
                medication_ndc = medication_ndc_map.get(ndc_code, None)
                if not medication_ndc:
                    try:
                        medication_ndc = \
                            MedicationNdc.objects.get(
                                ndc=ndc_code
                            )
                    except IntegrityError:
                        lost_ndcs.append((med_name, ndc_code))
                        pass

            if medication_ndc:
                # Add the actual medication (whatever it is) to the medication
                # map. We will use as key the ndc which is supossed to be a
                # real life id which should be unique, the value will be the
                # object that we can get. Python get from dict uses much
                # less programmatic time than a SQL get.

                medication_ndc_map[medication_ndc.ndc] = medication_ndc
            if provider and medication_ndc:
                # Create or update the relation object
                ProviderMedicationNdcThrough.objects.create(
                    provider=provider,
                    medication_ndc=medication_ndc,
                    supply=row.get('supply_level'),
                    latest=True
                )
                if provider not in updated_providers:
                    updated_providers.append(provider.id)
        else:
            lost_ndcs.append((med_name, ndc_code))

    # Finnally update the last_import_date in all the updated_providers
    if updated_providers:
        Provider.objects.filter(
            id__in=updated_providers,
        ).update(
            last_import_date=timezone.now(),
        )
    # Make celery delete the csv file in cache
    if temporary_file_obj:
        cache.delete(cache_key)

    # Send to sentry not found ndcs
    if lost_ndcs:
        if email_to:
            msg_plain = 'Lost medications during import on {}:\n'.format(
                timezone.now().strftime('%Y-%m-%d %H:%M')
            )
            for medication, ndc in lost_ndcs:
                msg_plain += '{}. ndc: {}\n'.format(medication, ndc)
            msg_plain += (
                '\nPlease check if the provided NDCs are correct. If you are '
                'sure they are correct and the problem persists, '
                'please, contact someone from the MedFinder staff.'
            )
            send_mail(
                'MedFinder Import',
                msg_plain,
                settings.FROM_EMAIL,
                [email_to],
            )
        raise ValidationError(
            'Following ndcs does not exist or exists in the database with '
            'another medication name, therefore they were not imported'
            ': {}'.format(lost_ndcs)
        )
    else:
        if email_to:
            msg_plain = 'All CSV rows correctly imported on {}'.format(
                timezone.now().strftime('%Y-%m-%d %H:%M')
            )
            send_mail(
                'MedFinder Import',
                msg_plain,
                settings.FROM_EMAIL,
                [email_to],
            )


# Task that handles the post_save signal asynchronously
@task(name="handle_provider_medication_through_post_save_signal")
def handle_provider_medication_through_post_save_signal(
    instance_pk,
    provider_pk,
    medication_ndc_pk
):
    ProviderMedicationNdcThrough.objects.filter(
        provider__pk=provider_pk,
        medication_ndc__pk=medication_ndc_pk,
    ).exclude(
        pk=instance_pk,
    ).update(
        latest=False,
    )


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


@shared_task
def mark_inactive_providers():
    filter_date = timezone.now() - timedelta(days=15)
    Provider.objects.filter(
        last_import_date__lte=filter_date,
    ).update(
        active=False,
    )

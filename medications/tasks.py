import re
import io
import boto3
from botocore.client import Config
import csv

from datetime import datetime
from time import sleep

from celery import shared_task
from celery.decorators import task
from datetime import timedelta
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import MultipleObjectsReturned
from django.core.mail import send_mail
from django.db import IntegrityError
from django.db.models import Count
from django.utils import timezone
from django.utils.timezone import get_current_timezone
from io import BytesIO
from urllib.request import urlopen
from zipfile import ZipFile

from auth_ex.models import User

from .models import (
    County,
    ExistingMedication,
    Medication,
    MedicationName,
    MedicationNdc,
    Organization,
    Provider,
    ProviderMedicationNdcThrough,
    State,
    ZipCode,
)


@shared_task
# This task can't be atomic because we need to run a post_save signal for
# every ProviderMedicationThrough object created
def generate_medications(cache_key, organization_id, email_to, import_date=False):

    def notify_by_email(email_to, beginning_time, index):
        finnish_time = timezone.now()
        duration = finnish_time - beginning_time
        duration_seconds = duration.seconds
        tz = timezone.pytz.timezone('EST')
        est_finnish_time = datetime.now(tz)

        msg_plain = (
            'Completion date time: {}\n'
            'Duration: {} seconds\n'
            'Status: {} CSV rows correctly imported.\n'
        ).format(
            est_finnish_time.strftime('%Y-%m-%d %H:%M'),
            duration_seconds,
            index,
        )
        send_mail(
            'MedFinder Import Status',
            msg_plain,
            settings.FROM_EMAIL,
            [email_to],
        )

    def get_provider_id(store_data, organization_id, provider_map):
        store_number = store_data['store_number']

        if str(store_number) in provider_map:
            return provider_map[str(store_number)]

        provider, created = Provider.objects.get_or_create(
            defaults=store_data,
            organization_id=organization_id,
            store_number=store_number,
        )

        if created:
            try:
                zipcode_obj = ZipCode.objects.get(zipcode=store_data['zip'])
            except MultipleObjectsReturned:
                zipcode_obj = ZipCode.objects.filter(
                    zipcode=store_data['zip'])[0]
            except ZipCode.DoesNotExist:
                zipcode_obj = None

            if zipcode_obj:
                provider.related_zipcode = zipcode_obj
                provider.save()

        return provider.id

    def find_missing_medication_ids(medication_data, medication_ndc_map, ndc_to_medication_map, medication_id_to_ndc_code_map):
        all_med_ids = list(set(ndc_to_medication_map.values()))

        medication_ids = []
        for data in medication_data:
            medication_ids.append(
                ndc_to_medication_map[find_medication_ndc_id(data, medication_ndc_map)])

        for medication_id in medication_ids:
            all_med_ids.remove(medication_id)

        return all_med_ids

    def add_no_report_entries(medication_data, missing_medication_ids, medication_id_to_ndc_code_map):
        for missing_medication_id in missing_medication_ids:
            medication_data.append({
                'level': -1,
                'ndc_code': medication_id_to_ndc_code_map[missing_medication_id],
                'supply': 'NO REPORT',
            })
        return medication_data

    def prepare_medication_data(provider_id, medication_data, number_of_medication_to_create, import_date, medication_ndc_map, ndc_to_medication_map, medication_id_to_ndc_code_map):
        if len(medication_data) != number_of_medication_to_create:
            missing_medication_ids = find_missing_medication_ids(
                medication_data, medication_ndc_map, ndc_to_medication_map, medication_id_to_ndc_code_map)
            medication_data = add_no_report_entries(
                medication_data, missing_medication_ids, medication_id_to_ndc_code_map)

        provider_medication_ndc_throughs = build_ProviderMedicationNdcThrough_objects(
            provider_id, medication_data, import_date, medication_ndc_map)

        return provider_medication_ndc_throughs

    def find_medication_ndc_id(data, medication_ndc_map):
        if data['ndc_code'] in medication_ndc_map:
            return medication_ndc_map[data['ndc_code']]
        else:
            return False

    def build_ProviderMedicationNdcThrough_objects(provider_id, medication_data, import_date, medication_ndc_map):
        objects = []

        for data in medication_data:
            objects.append(build_ProviderMedicationNdcThrough_object(
                data['supply'], data['level'], provider_id, find_medication_ndc_id(data, medication_ndc_map), import_date))

        return objects

    def build_ProviderMedicationNdcThrough_object(supply, level, provider_id, medication_ndc_id, import_date):
        if medication_ndc_id:
            if import_date:
                return ProviderMedicationNdcThrough(
                    creation_date=import_date,
                    date=import_date,
                    latest=False,
                    level=level,
                    medication_ndc_id=medication_ndc_id,
                    provider_id=provider_id,
                    supply=supply,
                )
            else:
                now = timezone.now()
                return ProviderMedicationNdcThrough(
                    creation_date=now,
                    date=now,
                    latest=True,
                    level=level,
                    medication_ndc_id=medication_ndc_id,
                    provider_id=provider_id,
                    supply=supply,
                )

    def prepare_current_store_data(store_data, medication_data, organization_id, number_of_medication_to_create, import_date, medication_ndc_map, ndc_to_medication_map, medication_id_to_ndc_code_map, provider_map):
        provider_id = get_provider_id(
            store_data, organization_id, provider_map)

        provider_medication_ndc_throughs = prepare_medication_data(provider_id, medication_data,
                                                                   number_of_medication_to_create, import_date, medication_ndc_map, ndc_to_medication_map, medication_id_to_ndc_code_map)

        return provider_medication_ndc_throughs, provider_id

    def mark_provider_has_active(updated_provider_ids):
        Provider.objects.filter(
            id__in=updated_provider_ids,
        ).update(
            last_import_date=timezone.now(),
            active=True,
        )

    def mark_previous_entries_as_past(older_than_me, updated_provider_ids):
        ProviderMedicationNdcThrough.objects.filter(
            creation_date__lt=older_than_me,
            latest=True,
            provider_id__in=updated_provider_ids,
        ).update(latest=False)

    def batch_create_provider_medication_ndc_throughs(provider_medication_ndc_throughs):
        ProviderMedicationNdcThrough.objects.bulk_create(
            provider_medication_ndc_throughs)

    beginning_time = timezone.now()

    # A list to update the last_import_date field in
    # all providers during this import
    updated_provider_ids = []

    number_of_medication_to_create = Medication.objects.count()
    organization = Organization.objects.get(pk=organization_id)
    existing_ndc_codes = ExistingMedication.objects.values_list(
        'ndc',
        flat=True,
    )
    provider = None
    medication_ndc = None
    medication_ndc_map = {}  # Use this map to save queries to the DB
    ndc_to_medication_map = {}
    medication_id_to_ndc_code_map = {}

    for ndc_entry in MedicationNdc.objects.all():
        medication_ndc_map[ndc_entry.ndc] = ndc_entry.id
        ndc_to_medication_map[ndc_entry.id] = ndc_entry.medication_id
        medication_id_to_ndc_code_map[ndc_entry.medication_id] = ndc_entry.ndc

    provider_map = {}  # Use this map to save queries to the DB

    for provider in Provider.objects.filter(organization_id=organization_id):
        provider_map[str(provider.store_number)] = provider.id

    csv_file = cache.get(cache_key)
    temporary_file_obj = csv_file.open()
    decoded_file = temporary_file_obj.read().decode('utf-8').splitlines()
    reader = csv.DictReader(decoded_file)
    sorted_csv = sorted(reader, key=lambda d: float(d['store #']))
    index = 0

    currently_processing_store_number = False
    current_store_data = {}
    current_store_medications_data = {}

    provider_medication_ndc_throughs_to_batch_insert = []

    supply_to_level_map = {
        'NO REPORT': -1,
        'NO SUPPLY': 0,
        '<24': 1,
        '24': 2,
        '24-48': 3,
        '>48': 4,
    }

    for row in sorted_csv:
        index += 1

        store_number = row.get('store #')
        supply_level = row.get('supply_level')
        level = supply_to_level_map.get(supply_level, 0)

        current_medication_data = {
            'level': level,
            'ndc_code': row.get('med_code'),
            'supply': supply_level,
        }

        if currently_processing_store_number == store_number:
            current_store_medications_data.append(current_medication_data)
        else:
            if currently_processing_store_number:
                provider_medication_ndc_throughs, provider_id = prepare_current_store_data(
                    current_store_data, current_store_medications_data, organization_id, number_of_medication_to_create, import_date, medication_ndc_map, ndc_to_medication_map, medication_id_to_ndc_code_map, provider_map)

                provider_medication_ndc_throughs_to_batch_insert = provider_medication_ndc_throughs_to_batch_insert + \
                    provider_medication_ndc_throughs

                if provider_id not in updated_provider_ids:
                    updated_provider_ids.append(provider_id)

            currently_processing_store_number = store_number
            current_store_medications_data = [current_medication_data]
            current_store_data = {
                'address': row.get('address'),
                'city': row.get('city'),
                'phone': row.get('phone'),
                'state': row.get('state'),
                'store_number': store_number,
                'zip': row.get('zipcode'),
            }

    batch_create_provider_medication_ndc_throughs(
        provider_medication_ndc_throughs_to_batch_insert)

    # Mark previous ProviderMedicationNdcThrough as past
    mark_previous_entries_as_past(beginning_time, updated_provider_ids)

    # Finally update the last_import_date in all the updated_providers
    mark_provider_has_active(updated_provider_ids)

    # Make celery delete the csv file in cache
    if temporary_file_obj:
        cache.delete(cache_key)

    # Send mail not found ndcs
    if email_to:
        notify_by_email(email_to, beginning_time, index)


# Task that handles the post_save signal asynchronously
@task(name="handle_provider_medication_through_post_save_signal")
def handle_provider_medication_through_post_save_signal(
    instance_pk,
    provider_pk,
    medication_ndc_pk,
):
    ProviderMedicationNdcThrough.objects.filter(
        provider_id=provider_pk,
        medication_ndc_id=medication_ndc_pk,
        latest=True,
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


@shared_task
def generate_csv_export(filename, file_url, user_id, med_id, start_date, end_date, med_ndc_ids, provider_type_list=[], provider_category_list=[], drug_type_list=[], state_id=None, zipcode=None):
    user = User.objects.get(pk=user_id)
    # First we take list of provider medication for this med, we will
    # use it for future filters
    if zipcode:
        provider_medication_qs = ProviderMedicationNdcThrough.objects.filter(  # noqa
            medication_ndc__medication__medication_name__id=med_id,
            provider__related_zipcode__zipcode=zipcode,
            provider__active=True,
        )
    elif not zipcode and state_id:
        provider_medication_qs = ProviderMedicationNdcThrough.objects.filter(  # noqa
            medication_ndc__medication__medication_name__id=med_id,
            provider__related_zipcode__state=state_id,
            provider__active=True,
        )
    else:
        provider_medication_qs = ProviderMedicationNdcThrough.objects.filter(  # noqa
            medication_ndc__medication__medication_name__id=med_id,
            provider__active=True,
        )

    provider_medication_qs = provider_medication_qs.filter(
        medication_ndc_id__in=med_ndc_ids,
    )

    if provider_type_list:
        provider_medication_qs = provider_medication_qs.filter(
            provider__type__in=provider_type_list,
        )

    if provider_category_list:
        provider_medication_qs = provider_medication_qs.filter(
            provider__category__in=provider_category_list,
        )

    if drug_type_list:
        provider_medication_qs = provider_medication_qs.filter(
            medication_ndc__medication__drug_type__in=drug_type_list,
        )

    tz = get_current_timezone()
    end_date = tz.localize(datetime.strptime(end_date, "%Y-%m-%d"))
    start_date = tz.localize(datetime.strptime(start_date, "%Y-%m-%d"))

    qs = ProviderMedicationNdcThrough.objects.filter(
        creation_date__gte=start_date,
        creation_date__lte=end_date + timedelta(days=1),
    ).prefetch_related(
        'provider',
        'provider__organization',
        'provider__type',
        'provider__category',
        'medication_ndc__medication',
        'medication_ndc__medication__medication_name',
    )

    national_level_permission = \
        user.permission_level == User.NATIONAL_LEVEL

    # Generate the name for the file
    if zipcode:
        geography = zipcode
    elif state_id:
        try:
            geography = State.objects.get(id=state_id).state_name
        except State.DoesNotExist:
            return False
    else:
        geography = 'US'

    try:
        med_name = MedicationName.objects.get(id=med_id)
    except MedicationName.DoesNotExist:
        return False

    if national_level_permission:
        header = [
            'Date',
            'Organization',
            'Provider ID',
            'Provider Name',
            'Provider Address',
            'Provider City',
            'Provider State',
            'Provider Zip',
            'Provider Type',
            'Pharmacy Category',
            'Medication Name',
            'Med ID',
            'Product Type',
            'Inventory',
            'Last Updated',
            'Latest',
        ]
    else:
        header = [
            'Date',
            'Provider City',
            'Provider State',
            'Provider Zip',
            'Medication Name',
            'Med ID',
            'Product Type',
            'Inventory',
            'Last Updated',
            'Latest',
        ]
    buff = io.StringIO()
    writer = csv.DictWriter(buff, fieldnames=header)
    writer.writeheader()
    for instance in qs:
        if national_level_permission:
            data_row = (
                instance.creation_date.date().isoformat(),
                instance.provider.organization,
                instance.provider.store_number,
                instance.provider.name,
                instance.provider.address,
                instance.provider.city,
                instance.provider.state,
                instance.provider.zip,
                instance.provider.type,
                instance.provider.category,
                instance.medication_ndc.medication.medication_name,
                instance.medication_ndc.medication.name,
                dict(Medication.DRUG_TYPE_CHOICES).get(
                    instance.medication_ndc.medication.drug_type
                ),
                instance.supply,
                instance.last_modified.ctime(),
                instance.latest,
            )
        else:
            data_row = (
                instance.creation_date.date().isoformat(),

                instance.provider.city,
                instance.provider.state,
                instance.provider.zip,
                instance.medication_ndc.medication.medication_name,
                instance.medication_ndc.medication.name,
                dict(Medication.DRUG_TYPE_CHOICES).get(
                    instance.medication_ndc.medication.drug_type
                ),
                instance.supply,
                instance.last_modified.ctime(),
                instance.latest,
            )
        writer.writerow(dict(zip(header, data_row)))

    buff = io.BytesIO(buff.getvalue().encode())
    client = boto3.client('s3')
    client.upload_fileobj(buff, settings.AWS_S3_BUCKET_NAME, filename)

    delete_csv_file_on_s3.apply_async([filename], countdown=60 * 60 * 24)

    msg_plain = (
        'CSV File is ready to download\n'
        '\n'
        '{}\n'
        '\n'
        'Url will expire in 24 hours \n'
    ).format(
        file_url,
    )
    send_mail(
        'MedFinder - CSV Export',
        msg_plain,
        settings.FROM_EMAIL,
        [user.email],
    )


@shared_task
def delete_csv_file_on_s3(filename):
    boto3.resource('s3').Object(settings.AWS_S3_BUCKET_NAME, filename).delete()

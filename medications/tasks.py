import re
import io
import boto3
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
    beginning_time = timezone.now()
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
    index = 0
    for row in reader:
        index += 1
        if index % 30000 == 0:
            sleep(30)
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
                default_provider_data = {'phone': phone, 'city': city, 'state': state,
                                         'address': address, 'zip': zip_code, 'related_zipcode': zipcode_obj}
                provider, created = Provider.objects.get_or_create(
                    organization=organization,
                    store_number=store_number,
                    defaults=default_provider_data
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
                    except (
                        IntegrityError,
                        MedicationNdc.DoesNotExist,
                    ):
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
                if import_date:
                    ProviderMedicationNdcThrough.objects.create(
                        provider=provider,
                        medication_ndc=medication_ndc,
                        supply=row.get('supply_level'),
                        latest=False,
                        creation_date=import_date,
                        last_modified=import_date,
                    )
                else:
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
            active=True,
        )
    # Make celery delete the csv file in cache
    if temporary_file_obj:
        cache.delete(cache_key)

    # Send mail not found ndcs
    if email_to:
        finnish_time = timezone.now()
        duration = finnish_time - beginning_time
        duration_minutes = round(duration.seconds / 60, 0)
        tz = timezone.pytz.timezone('EST')
        est_finnish_time = datetime.now(tz)

        if lost_ndcs:
            msg_plain = (
                'Completion date time: {}\n'
                'Duration: {} minutes\n'
                'Status: {} rows processed\n'
                '{} CSV entries were not imported\n'
            ).format(
                est_finnish_time.strftime('%Y-%m-%d %H:%M'),
                duration_minutes,
                index,
                len(lost_ndcs),
            )
        else:
            msg_plain = (
                'Completion date time: {}\n'
                'Duration: {} minutes\n'
                'Status: {} CSV rows correctly imported.\n'
            ).format(
                est_finnish_time.strftime('%Y-%m-%d %H:%M'),
                duration_minutes,
                index,
            )
        send_mail(
            'MedFinder Import Status',
            msg_plain,
            settings.FROM_EMAIL,
            [email_to],
        )


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
def state_cache_provider_count():
    cache_provider_count(State, 'state_zipcodes__providers')


@shared_task
def county_cache_provider_count():
    cache_provider_count(County, 'county_zipcodes__providers')


@shared_task
def zipcode_cache_provider_count():
    cache_provider_count(ZipCode, 'providers')


def cache_provider_count(model, count_entities):
    cached_counts = {}

    total_provider_count = model.objects.annotate(
        calculated_total_provider_count=Count(count_entities)
    ).values('id', 'calculated_total_provider_count').distinct()

    if model == ZipCode:
        active_provider_count = model.objects.filter(
            providers__active=True,
        )
    if model == State:
        active_provider_count = model.objects.filter(
            state_zipcodes__providers__active=True,
        )
    if model == County:
        active_provider_count = model.objects.filter(
            county_zipcodes__providers__active=True,
        )

    active_provider_count = active_provider_count.annotate(
        calculated_active_provider_count=Count(count_entities)
    ).values('id', 'calculated_active_provider_count').distinct()

    for provider_count in total_provider_count:
        if not provider_count['id'] in cached_counts:
            cached_counts[provider_count['id']] = {}
        cached_counts[provider_count['id']
                      ]['calculated_total_provider_count'] = provider_count['calculated_total_provider_count']

    for provider_count in active_provider_count:
        if not provider_count['id'] in cached_counts:
            cached_counts[provider_count['id']] = {}
        cached_counts[provider_count['id']
                      ]['calculated_active_provider_count'] = provider_count['calculated_active_provider_count']

    for entity in model.objects.all():
        if entity.pk in cached_counts:
            entity.active_provider_count = cached_counts[entity.pk][
                'calculated_active_provider_count'] if 'calculated_active_provider_count' in cached_counts[entity.pk] else 0
            entity.total_provider_count = cached_counts[entity.pk][
                'calculated_total_provider_count'] if 'calculated_total_provider_count' in cached_counts[entity.pk] else 0
        else:
            print('State cache count not found for ' + str(entity))
        entity.save()


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

    if provider_type_list:
        try:
            provider_type_list = provider_type_list.split(',')
            provider_medication_qs = provider_medication_qs.filter(
                provider__type__in=provider_type_list,
            )
        except ValueError:
            pass

    provider_medication_qs = provider_medication_qs.filter(
        medication_ndc_id__in=med_ndc_ids,
    )

    if provider_category_list:
        try:
            provider_category_list = provider_category_list.split(',')
            provider_medication_qs = provider_medication_qs.filter(
                provider__category__in=provider_category_list,
            )
        except ValueError:
            pass

    if drug_type_list:
        try:
            drug_type_list = drug_type_list.split(',')
            provider_medication_qs = provider_medication_qs.filter(
                medication_ndc__medication__drug_type__in=drug_type_list,
            )
        except ValueError:
            pass

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

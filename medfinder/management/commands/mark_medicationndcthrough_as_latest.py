import time
from datetime import datetime

from django.db.models import Max

from django.core.management.base import BaseCommand

from medications.models import ProviderMedicationNdcThrough

# heroku run python manage.py mark_medicationndcthrough_as_latest -a medfinder-api
# python manage.py mark_medicationndcthrough_as_latest
# docker-compose -f dev.yml run django python manage.py mark_medicationndcthrough_as_latest


class Command(BaseCommand):
    """
    Import from Vaccine Finder DB to populate provider type
    """
    help = 'Import from Vaccine Finder DB to provider type'

    def handle(self, *args, **options):
        print("STARTING mark_medicationndcthrough_as_latest")
        self.mark_medicationndcthrough_as_latest()

    def mark_medicationndcthrough_as_latest(self):
        provider_medication_ndcs = ProviderMedicationNdcThrough.objects.filter(
            latest=True)

        provider_count = provider_medication_ndcs.count()
        index = 0
        for provider_medication_ndc in provider_medication_ndcs:
            medication_ndc_id = provider_medication_ndc.medication_ndc_id
            provider_id = provider_medication_ndc.provider_id

            latest_entry = ProviderMedicationNdcThrough.objects.filter(
                provider_id=provider_id, medication_ndc_id=medication_ndc_id).order_by('-creation_date')[:1][0]

            ProviderMedicationNdcThrough.objects.filter(
                provider_id=provider_id, medication_ndc_id=medication_ndc_id).update(latest=False)

            latest_entry.latest = True
            latest_entry.save()

            index = index + 1
            print(str(index) + '/' + str(provider_count))

import time
from datetime import datetime

from django.db.models import Max

from django.core.management.base import BaseCommand

from medications.models import ProviderMedicationNdcThrough


class Command(BaseCommand):
    """
    Import from Vaccine Finder DB to populate provider type
    """
    help = 'Import from Vaccine Finder DB to provider type'

    def handle(self, *args, **options):
        self.mark_medicationndcthrough_as_latest()

    def mark_medicationndcthrough_as_latest(self):
        provider_medication_ndcs = ProviderMedicationNdcThrough.objects.filter(
            latest=True)

        print(provider_medication_ndcs.count())

        for provider_medication_ndc in provider_medication_ndcs:
            medication_ndc_id = provider_medication_ndc.medication_ndc_id
            provider_id = provider_medication_ndc.provider_id

            latest_entry = ProviderMedicationNdcThrough.objects.filter(
                provider_id=provider_id, medication_ndc_id=medication_ndc_id).order_by('-last_modified')[:1][0]

            ProviderMedicationNdcThrough.objects.filter(
                provider_id=provider_id, medication_ndc_id=medication_ndc_id).update(latest=False)

            latest_entry.latest = True
            latest_entry.save()

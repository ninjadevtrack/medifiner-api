import csv

from django.core.management.base import BaseCommand
from django.db import IntegrityError

from medications.models import Medication, MedicationName, MedicationNdc


class Command(BaseCommand):
    """
    Import medications from csv file in your local machine
    """
    help = 'Populate db with medication data'

    def handle(self, *args, **options):
        with open('example_medications.csv') as file:
            decoded_file = file.read().splitlines()
            reader = csv.DictReader(decoded_file)
            for row in reader:
                full_name = row.get('name')
                ndc = row.get('ndc')
                type_med = row.get('type').lower()
                med_name = row.get('medication name')
                medication_name, _ = MedicationName.objects.get_or_create(
                    name=med_name,
                )
                try:
                    medication, created = Medication.objects.get_or_create(
                        name=full_name,
                        medication_name=medication_name,
                        drug_type=type_med
                    )
                    medication_ndc, created = MedicationNdc.objects.get_or_create( # noqa
                        medication=medication,
                        ndc=ndc
                    )
                except IntegrityError:
                    pass

import csv
import os
import pytest

from django.core.files import File

from medications.models import (
    Organization,
    TemporaryFile,
    ExistingMedication,
    ProviderMedicationThrough,
)
from medications.constants import field_rows
from medications.tasks import generate_medications

pytestmark = pytest.mark.django_db()


@pytest.fixture()
def organization():
    return Organization.objects.create(
        organization_name='test organization',
    )


class TestGenerateMedicationsTask:
    ndc_code = '0002-1433-80'
    fake_med = 'Focusyn'
    fake_store_number = '123'
    fake_med_provider_data = [
        fake_store_number,
        '742 Evergreen Terrace',
        'Springfield',
        '65619',
        'MO',
        '417-555-7334',
        ndc_code,
        fake_med,
        'NO SUPPLY',
    ]
    # Generate fake medication and provider data to add to the csv and to
    # compare if the Provider Medication model has been created by the task
    # with the correct information.

    @pytest.fixture(autouse=True)
    def setup_stuff(self, db, organization):
        self.organization = organization
        ExistingMedication.objects.create(ndc=self.ndc_code)
        csv_file = open('temporal.csv', 'w+', newline='')
        filewriter = csv.writer(
            csv_file,
            delimiter=',',
            quotechar='|',
            quoting=csv.QUOTE_MINIMAL,
        )
        filewriter.writerow(field_rows)
        filewriter.writerow(self.fake_med_provider_data)
        csv_file.seek(0)
        self.csv_file = File(csv_file)
        self.temporary_file = TemporaryFile.objects.create(file=self.csv_file)
        csv_file.close()

    def test_generate_medications_task(self):
        generate_medications(self.temporary_file.id, self.organization.id)
        try:
            ProviderMedicationThrough.objects.get(
                medication__name=self.fake_med,
                medication__ndc=self.ndc_code,
                provider__store_number=self.fake_store_number,
            )
        except ProviderMedicationThrough.DoesNotExist:
            raise pytest.fail(
                'Test Failed: ProviderMedicationThrough model not found'
            )

    @classmethod
    def teardown_class(cls):
        os.remove('temporal.csv')

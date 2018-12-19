import time
from datetime import datetime

from django.core.management.base import BaseCommand

from medications.models import Organization, Provider, ProviderType
from vaccinefinder.models import VFOrganization, VFProvider


# docker-compose -f dev.yml run django python manage.py vaccinefinder_import
class Command(BaseCommand):
    """
    Import from Vaccine Finder DB to populate provider type
    """
    help = 'Import from Vaccine Finder DB to provider type'

    def handle(self, *args, **options):
        self.import_providers_from_remote_db()

    def find_provider_type(self, vaccinefinder_type_id):
        type = self.vaccine_finder_type_map(vaccinefinder_type_id)
        if type:
            provider_type, created = ProviderType.objects.get_or_create(
                name=type)
            return provider_type
        else:
            return None

    def vaccine_finder_type_map(self, vaccinefinder_type_id):
        types = {
            1: "Clinic",
            2: "Health Department",
            3: "Healthcare Provider’s Office",
            4: "Pharmacy",
            5: "Community Provider / Immunizer",
            6: "Tribal Health Center",
        }
        return types[vaccinefinder_type_id] if vaccinefinder_type_id != 0 else None

    def import_providers_from_remote_db(self):
        present = datetime.now().replace(tzinfo=None)

        provider_type, created = ProviderType.objects.get_or_create(
            code='CO',
            name='Commercial',
        )

        vaccine_finder_orgs = VFOrganization.objects.using('vaccinedb').all()

        for vaccine_finder_org in vaccine_finder_orgs:
            try:
                organization, created = Organization.objects.using(
                    'default').get_or_create(
                    contact_name=vaccine_finder_org.contact_name,
                    organization_name=vaccine_finder_org.organization_name,
                    phone=vaccine_finder_org.phone,
                    website=vaccine_finder_org.website
                )
            except:
                print("Organization could not be created")
                continue

            for vaccine_finder_provider in vaccine_finder_org.vfproviders.all():
                try:
                    provider, created = Provider.objects.get_or_create(
                        address=vaccine_finder_provider.address,
                        city=vaccine_finder_provider.city,
                        email=vaccine_finder_provider.email,
                        end_date=vaccine_finder_provider.end_date,
                        insurance_accepted=(
                            True if vaccine_finder_provider.insurance_accepted == 'Y' else False),
                        lat=vaccine_finder_provider.lat,
                        lng=vaccine_finder_provider.lon,
                        name=vaccine_finder_provider.name,
                        notes=vaccine_finder_provider.notes,
                        operating_hours=vaccine_finder_provider.operating_hours,
                        organization=organization,
                        phone=vaccine_finder_provider.phone,
                        relate_related_zipcode=True,
                        start_date=vaccine_finder_provider.start_date,
                        state=vaccine_finder_provider.state,
                        store_number=vaccine_finder_provider.store_number,
                        website=vaccine_finder_provider.website,
                        active=False,
                        walkins_accepted=(
                            True if vaccine_finder_provider.walkins_accepted == 'Y' else False),
                        zip=vaccine_finder_provider.zip,
                    )

                    if vaccine_finder_provider.type == 4:
                        provider.type = provider_type
                    else:
                        provider.type = self.find_provider_type(
                            vaccine_finder_provider.type)

                    provider.save()

                except:
                    print('Provider could not be created')

            time.sleep(30)

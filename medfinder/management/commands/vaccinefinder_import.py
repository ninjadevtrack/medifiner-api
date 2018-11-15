from datetime import datetime

from django.core.management.base import BaseCommand

from medications.models import Organization, Provider, ProviderType
from vaccinefinder.models import VFOrganization, VFProvider


class Command(BaseCommand):
    """
    Import from Vaccine Finder DB to populate provider type
    """
    help = 'Import from Vaccine Finder DB to provider type'

    def handle(self, *args, **options):
        self.import_providers_from_remote_db()

    # def relate_related_zipcode(self, organization):
    #     organization = Organization.objects.filter(
    #         organization_name='Walgreens',
    #     )[0]
    #     for provider in organization.providers.all():
    #         provider.relate_related_zipcode = True
    #         provider.save()

    def import_providers_from_remote_db(self):
        walgreens_id = 102
        present = datetime.now().replace(tzinfo=None)

        provider_type, created = ProviderType.objects.get_or_create(
            code='CO',
            name='Commercial',
        )

        vaccine_finder_orgs = VFOrganization.objects.using(
            'vaccinedb').exclude(pk=walgreens_id).all()

        for vaccine_finder_org in vaccine_finder_orgs:
            organization, created = Organization.objects.using(
                'default').get_or_create(
                contact_name=vaccine_finder_org.contact_name,
                organization_name=vaccine_finder_org.organization_name,
                phone=vaccine_finder_org.phone,
                website=vaccine_finder_org.website
            )

            already_imported_store_numbers = list(organization.providers.values_list(
                'store_number',
                flat=True,
            ))

            print(already_imported_store_numbers)

            count = 0
            for vaccine_finder_provider in vaccine_finder_org.vfproviders.exclude(store_number__in=already_imported_store_numbers):
                provider = Provider.objects.create(
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
                    type=provider_type,
                    website=vaccine_finder_provider.website,
                    active=False,
                    walkins_accepted=(
                        True if vaccine_finder_provider.walkins_accepted == 'Y' else False),
                    zip=vaccine_finder_provider.zip,
                )
                count += 1

            print("------------------------------------")
            print("Imported")
            print(vaccine_finder_org.organization_name)
            print(count)

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
        self.sync_providers()

        # self.add_missing_providers()
        # self.update_provider_info()

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

    def add_missing_providers(self):
        provider_type, created = ProviderType.objects.get_or_create(
            code='CO',
            name='Commercial',
        )

        vf_orgs = VFOrganization.objects.using('vaccinedb').all()

        for vf_org in vf_orgs:
            organization = Organization.objects.get(
                vaccine_finder_id=vf_org.organization_id)

            already_existing_provider_vaccine_finder_ids = Provider.objects.filter(
                organization_id=organization.id).value_list('vaccine_finder_id', flat=True)

            for vaccine_finder_provider in vf_org.vfproviders.exclude(provider_id__in=already_existing_provider_vaccine_finder_ids):
                Provider.objects.get_or_create(
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
                    vaccine_finder_id=vaccine_finder_provider.provider_id,
                    type=(provider_type if vaccine_finder_provider.type == 4 else self.find_provider_type(
                        vaccine_finder_provider.type)),
                    vaccine_finder_type=vaccine_finder_provider.type
                )

    def update_provider_info(self):
        provider_type, created = ProviderType.objects.get_or_create(
            code='CO',
            name='Commercial',
        )

        for provider in Provider.objects.all():
            vaccine_finder_provider = VFProvider.objects.get(
                provider_id=provider.vaccine_finder_id)

            provider.address = vaccine_finder_provider.address
            provider.city = vaccine_finder_provider.city
            provider.email = vaccine_finder_provider.email
            provider.end_date = vaccine_finder_provider.end_date
            provider.insurance_accepted = (
                True if vaccine_finder_provider.insurance_accepted == 'Y' else False)
            provider.lat = vaccine_finder_provider.lat
            provider.lng = vaccine_finder_provider.lon
            provider.name = vaccine_finder_provider.name
            provider.notes = vaccine_finder_provider.notes
            provider.operating_hours = vaccine_finder_provider.operating_hours
            provider.organization = organization
            provider.phone = vaccine_finder_provider.phone
            provider.relate_related_zipcode = True
            provider.start_date = vaccine_finder_provider.start_date
            provider.state = vaccine_finder_provider.state
            provider.store_number = vaccine_finder_provider.store_number
            provider.website = vaccine_finder_provider.website
            provider.active = False
            provider.walkins_accepted = (
                True if vaccine_finder_provider.walkins_accepted == 'Y' else False)
            provider.zip = vaccine_finder_provider.zip
            provider.vaccine_finder_id = vaccine_finder_provider.provider_id
            provider.type = (provider_type if vaccine_finder_provider.type == 4 else self.find_provider_type(
                vaccine_finder_provider.type))
            provider.vaccine_finder_type = vaccine_finder_provider.type
            provider.save()

    def sync_providers(self):
        provider_type, created = ProviderType.objects.get_or_create(
            code='CO',
            name='Commercial',
        )

        organization_ids_to_treat = Provider.objects.filter(
            vaccine_finder_id__isnull=True).values_list('organization_id', flat=True)
        organization_ids_to_treat = set(list(organization_ids_to_treat))

        organizations = Organization.objects.using(
            'default').exclude(id=5).filter(id__in=organization_ids_to_treat)

        for organization in organizations:

            vf_orgs = VFOrganization.objects.using('vaccinedb').filter(
                organization_id=organization.vaccine_finder_id)

            vf_org = vf_orgs[0]

            already_processed_provider_ids = Provider.objects.filter(
                organization=organization,
                vaccine_finder_id__isnull=False
            ).values_list('vaccine_finder_id', flat=True)

            already_processed_provider_ids = list(
                already_processed_provider_ids)

            for vaccine_finder_provider in vf_org.vfproviders.exclude(provider_id__in=already_processed_provider_ids):
                Provider.objects.get_or_create(
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
                    vaccine_finder_id=vaccine_finder_provider.provider_id,
                    type=(provider_type if vaccine_finder_provider.type == 4 else self.find_provider_type(
                        vaccine_finder_provider.type)),
                    vaccine_finder_type=vaccine_finder_provider.type
                )

            # DELETE all providers not linked to VF
            Provider.objects.filter(
                organization=organization,
                vaccine_finder_id__isnull=True
            ).delete()

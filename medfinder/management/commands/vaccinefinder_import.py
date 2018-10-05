import csv
import requests

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from medications.models import Organization, Provider, ProviderType, ZipCode
from vaccinefinder.models import Organization as VFOrg


class Command(BaseCommand):
    """
    Import from Vaccine Finder DB to populate provider type
    """
    help = 'Import from Vaccine Finder DB to provider type'

    def handle(self, *args, **options):
        self.import_providers_from_remote_db()
        self.relate_related_zipcode()

    def relate_related_zipcode(self):
        organization = Organization.objects.filter(
            organization_name='Walgreens',
        )[0]
        for provider in organization.providers.all():
            provider.relate_related_zipcode = True
            provider.save()

    def import_providers_from_remote_db(self):
        org_id = 102

        provider_type, created = ProviderType.objects.get_or_create(
            code='CO',
            name='Commercial',
        )

        walgreens_org = VFOrg.objects.using('vaccinedb').get(pk=org_id)

        organization = Organization.objects.create(
            contact_name=walgreens_org.contact_name,
            organization_name=walgreens_org.organization_name,
            phone=walgreens_org.phone,
            website=walgreens_org.website
        )

        for walgreen in walgreens_org.providers.all():
            provider = Provider.objects.create(
                address=walgreen.address,
                city=walgreen.city,
                email=walgreen.email,
                end_date=walgreen.end_date,
                home_delivery=walgreen.home_delivery,
                home_delivery_site=walgreen.home_delivery_site,
                insurance_accepted=(
                    True if walgreen.insurance_accepted == 'Y' else False),
                lat=walgreen.lat,
                lng=walgreen.lon,
                name=walgreen.name,
                notes=walgreen.notes,
                operating_hours=walgreen.operating_hours,
                organization=organization,
                phone=walgreen.phone,
                relate_related_zipcode=True,
                start_date=walgreen.start_date,
                state=walgreen.state,
                store_number=walgreen.store_number,
                type=provider_type,
                website=walgreen.website,
                walkins_accepted=(
                    True if walgreen.walkins_accepted == 'Y' else False),
                zip=walgreen.zip,
            )

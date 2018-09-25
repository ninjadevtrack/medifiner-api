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
                organization=organization,
                store_number=walgreen.store_number,
                name=walgreen.name,
                type=provider_type,
                address=walgreen.address,
                city=walgreen.city,
                state=walgreen.state,
                zip=walgreen.zip,
                phone=walgreen.phone,
                website=walgreen.website,
                email=walgreen.email,
                operating_hours=walgreen.operating_hours,
                notes=walgreen.notes,
                insurance_accepted=(
                    True if walgreen.insurance_accepted == 'Y' else False),
                lat=walgreen.lat,
                lng=walgreen.lon,
                start_date=walgreen.start_date,
                end_date=walgreen.end_date,
                relate_related_zipcode=True,
                walkins_accepted=(
                    True if walgreen.walkins_accepted == 'Y' else False),
            )

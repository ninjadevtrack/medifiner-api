import time
from datetime import datetime

from django.core.management.base import BaseCommand

from medications.models import Provider


class Command(BaseCommand):
    """
    Associate Provider and Zipcode
    """
    help = 'Associate Provider and Zipcode'

    def handle(self, *args, **options):
        self.associate_providers_and_zipcodes()

    def associate_providers_and_zipcodes(self):
        providers_with_no_zipcodes = Provider.objects.filter(
            related_zipcode=None)

        providers_with_no_zipcodes_count = providers_with_no_zipcodes.count()

        print(str(providers_with_no_zipcodes_count) + " providers found")

        index = 0
        for provider in providers_with_no_zipcodes:
            index = index + 1
            provider.relate_related_zipcode = True
            provider.save()
            print(str(index) + '/' + str(providers_with_no_zipcodes_count))

        providers_with_no_zipcodes_count = Provider.objects.filter(
            related_zipcode=None).count()

        print(str(providers_with_no_zipcodes_count) +
              " providers with no zipcode remaining")

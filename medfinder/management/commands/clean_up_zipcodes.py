from datetime import datetime

from django.core.management.base import BaseCommand

from django.db import connection

from medications.models import Provider, ZipCode


class Command(BaseCommand):
    """
    Import from Vaccine Finder DB to populate provider type
    """
    help = 'Import from Vaccine Finder DB to provider type'

    def handle(self, *args, **options):
        zipcodes = {}
        query = "SELECT id, zipcode FROM medications_zipcode WHERE zipcode IN ( SELECT zipcode FROM medications_zipcode GROUP BY zipcode HAVING COUNT(*) > 1) ORDER BY zipcode, id;"
        cursor = connection.cursor()
        cursor.execute(query)

        for row in cursor.fetchall():
            id = row[0]
            zipcode = row[1]
            if not zipcode in zipcodes:
                zipcodes[zipcode] = []
            zipcodes[zipcode].append(id)

        for zipcode, ids in zipcodes.items():
            id_to_keep = ids[0]

            for id_to_delete in ids:
                if id_to_delete != id_to_keep:
                    Provider.objects.filter(related_zipcode_id=id_to_delete).update(
                        related_zipcode_id=id_to_keep)

                    ZipCode.objects.get(pk=id_to_delete).delete()

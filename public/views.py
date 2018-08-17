from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from django.contrib.gis.geos import Point
from django.db.models import Q, Prefetch
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from django.contrib.postgres.aggregates import ArrayAgg

from medications.models import ProviderMedicationThrough, Provider
from .serializers import FindProviderSerializer


class FindProviderMedicationView(ListAPIView):
    serializer_class = FindProviderSerializer
    permission_classes = (AllowAny,)
    allowed_methods = ['GET']

    def get_queryset(self):
        med_id = self.request.query_params.get('med_id')
        formulation_id_raw = self.request.query_params.get(
            'formulation',
        )
        localization = self.request.query_params.get('localization')

        # Distance is given in miles
        distance = self.request.query_params.get('distance')
        if not distance:
            distance = 10

        # TODO: narrow for 'Brand Drugs', 'Generic Drugs' and
        # 'Public Health Supply'. Not implemented yet in models. Waiting
        # to NCPDP information to populate those
        if formulation_id_raw and med_id and localization:
            formulation_id = int(formulation_id_raw)
            provider_medication_qs = ProviderMedicationThrough.objects.filter(
                latest=True,
                medication__medication_name__id=med_id,
                medication__id=formulation_id,
                # TODO localization
            )
            provider_medication_ids = provider_medication_qs.values_list(
                'id',
                flat=True,
            )
        else:
            return None

        # test point used for development, to be taken from query params
        test_point = Point(41.7798226, -72.4372796, srid=4326)

        provider_qs = Provider.objects.filter(
            provider_medication__id__in=provider_medication_ids,
            geo_localization__distance_lte=(test_point, D(mi=distance)),
        ).annotate(
            distance=Distance(
                'geo_localization',
                test_point,
            ),
            medication_levels=ArrayAgg(
                'provider_medication__level',
                filter=Q(
                    provider_medication__id__in=provider_medication_ids
                )
            ),
        ).prefetch_related(
            Prefetch(
                'provider_medication',
                queryset=ProviderMedicationThrough.objects.filter(
                    latest=True,
                ).exclude(
                    id__in=provider_medication_ids,
                ).select_related(
                    'medication',
                )
            )
        )

        return provider_qs

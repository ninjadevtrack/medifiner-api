from rest_framework.generics import ListAPIView
from rest_registration.exceptions import BadRequest
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.contrib.gis.geos import Point
from django.db.models import Q, Prefetch
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from django.contrib.postgres.aggregates import ArrayAgg

from epidemic.models import Epidemic
from medications.models import (
    ProviderMedicationThrough,
    Provider,
    Medication,
)
from .serializers import FindProviderSerializer


class FindProviderMedicationView(ListAPIView):
    serializer_class = FindProviderSerializer
    permission_classes = (AllowAny,)
    allowed_methods = ['GET']

    def get_queryset(self):
        '''
        query_params:
            - med_ids: list of MedicaitonName ids
            - formulations: list of Medication ids
            - localization: list of 2 coordinates (must be int or float)
            - drug_type: list of 1 character str, for drug_type in Medication
            - distance: int, in miles
        '''
        med_ids_raw = self.request.query_params.get('med_ids')
        formulation_ids_raw = self.request.query_params.get(
            'formulations',
        )
        formulation_ids = []
        if formulation_ids_raw:
            try:
                formulation_ids = list(
                    map(int, formulation_ids_raw.split(','))
                )
            except ValueError:
                pass

        med_ids = []
        if med_ids_raw:
            try:
                med_ids = list(
                    map(int, med_ids_raw.split(','))
                )
            except ValueError:
                pass

        localization = self.request.query_params.get('localization')

        drug_type_list = self.request.query_params.get(
            'drug_type',
            [],
        )
        # Distance is given in miles
        distance = self.request.query_params.get('distance')
        if not distance:
            distance = 10

        try:
            localization = list(
                map(float, localization.split(','))
            )
            localization_point = Point(
                localization[0], localization[1], srid=4326,
            )
        except (IndexError, ValueError):
            raise BadRequest(
                'Localization should consist of 2 coordinates'
            )

        if formulation_ids and med_ids and localization:
            provider_medication_qs = ProviderMedicationThrough.objects.filter(
                latest=True,
                medication__medication_name__id__in=med_ids,
                medication__id__in=formulation_ids,
                provider__geo_localization__distance_lte=(
                    localization_point,
                    D(mi=distance),
                ),
            )

            # Check the list of drug types to filter
            if drug_type_list:
                try:
                    drug_type_list = drug_type_list.split(',')
                    provider_medication_qs = provider_medication_qs.filter(
                        medication__drug_type__in=drug_type_list,
                    )
                except ValueError:
                    pass
            provider_medication_ids = provider_medication_qs.values_list(
                'id',
                flat=True,
            )
        else:
            return None

        provider_qs = Provider.objects.filter(
            geo_localization__distance_lte=(
                localization_point,
                D(mi=distance),
            ),
        ).annotate(
            distance=Distance(
                'geo_localization',
                localization_point,
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
        ).order_by('distance')

        # TODO: other medications will be only if there is generoc nad brand
        # no other kind of medications

        # TODO
        # first show the highest supply if they have the same supply
        # then the generic

        # TODO in simple search if the same medication is brand an generic show
        # the generic

        return provider_qs


class BasicInfoView(APIView):

    def get(self, request):
        # Making a bigger response in case more objects are added in the future
        response = {}
        map_choices = dict(Medication.DRUG_TYPE_CHOICES)
        if not Epidemic.objects.first().active:
            map_choices.pop(Medication.PUBLIC_HEALTH_SUPPLY)
        response['drug_type'] = map_choices
        return Response(response)

from django.db.models import Q, Count
from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.gis.db.models.functions import Centroid, AsGeoJSON

from django.utils.translation import ugettext_lazy as _

from rest_framework import status, viewsets
from rest_framework.generics import GenericAPIView, ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from medications.tasks import generate_medications
from .serializers import (
    CSVUploadSerializer,
    MedicationNameSerializer,
    StateSerializer,
    GeoStateWithMedicationsSerializer,
    GeoCountyWithMedicationsSerializer,
    GeoZipCodeWithMedicationsSerializer,
    ProviderTypesSerializer,
)
from .models import (
    County,
    TemporaryFile,
    MedicationName,
    ProviderMedicationThrough,
    Provider,
    Medication,
    State,
    ZipCode,
)


class CSVUploadView(GenericAPIView):
    serializer_class = CSVUploadSerializer
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        csv_file = serializer.validated_data.pop('csv_file')
        organization_id = serializer.validated_data.pop('organization_id')
        temporary_csv_file = TemporaryFile.objects.create(file=csv_file)
        generate_medications.delay(
            temporary_csv_file.id,
            organization_id,
        )
        return Response(
            {'status': _('The medications creation proccess has been queued')},
            status=status.HTTP_200_OK,
        )


class MedicationNameViewSet(viewsets.ModelViewSet):
    serializer_class = MedicationNameSerializer
    permission_classes = (IsAuthenticated,)
    allowed_methods = ['GET']

    def get_queryset(self):
        return MedicationName.objects.prefetch_related('medications')


class StateViewSet(viewsets.ModelViewSet):
    serializer_class = StateSerializer
    permission_classes = (IsAuthenticated,)
    allowed_methods = ['GET']
    queryset = State.objects.all().annotate(
        county_list=ArrayAgg('counties__county_name'),
    )


class GeoStatsStatesWithMedicationsView(ListAPIView):
    serializer_class = GeoStateWithMedicationsSerializer
    permission_classes = (IsAuthenticated,)
    allowed_methods = ['GET']

    def get_queryset(self):
        med_id = self.request.query_params.get('med_id')
        try:
            if not med_id or int(
                med_id
            ) not in MedicationName.objects.values_list(
                'id',
                flat=True,
            ):
                return State.objects.none()
        except ValueError:
            return State.objects.none()

        # First we take list of provider medication for this med, we will
        # use it for future filters
        provider_medication_qs = ProviderMedicationThrough.objects.filter(
            latest=True,
            medication__medication_name__id=med_id,
        )

        # We take the formulation ids and transform them to use like filter
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
        if formulation_ids:
            provider_medication_qs = provider_medication_qs.filter(
                medication__id__in=formulation_ids,
            )

        # Now we check if there is a list of type of providers to filter
        provider_type_list = self.request.query_params.get(
            'provider_type',
            [],
        )
        if provider_type_list:
            provider_type_list = provider_type_list.split(',')
            provider_medication_qs = provider_medication_qs.filter(
                provider__type__in=provider_type_list,
            )

        # Annotate the list of the medication levels for every state
        # to be used to calculate the low/medium/high after in the serializer.
        # We create a list of the ids of the provider medication objects that
        # we have after filtering.
        provider_medication_ids = provider_medication_qs.values_list(
            'id',
            flat=True,
        )
        qs = State.objects.all().annotate(
            medication_levels=ArrayAgg(
                'state_zipcodes__providers__provider_medication__level',
                filter=Q(
                        state_zipcodes__providers__provider_medication__id__in=provider_medication_ids # noqa
                )
            ),
        )
        return qs


class GeoStatsCountiesWithMedicationsView(ListAPIView):
    serializer_class = GeoCountyWithMedicationsSerializer
    permission_classes = (IsAuthenticated,)
    allowed_methods = ['GET']

    def get_queryset(self):
        med_id = self.request.query_params.get('med_id')
        state = self.kwargs.pop('id')
        try:
            if not med_id or int(
                med_id
            ) not in MedicationName.objects.values_list(
                'id',
                flat=True,
            ):
                return County.objects.none()
        except ValueError:
            return County.objects.none()

        # First we take list of provider medication for this med, we will
        # use it for future filters
        provider_medication_qs = ProviderMedicationThrough.objects.filter(
            latest=True,
            medication__medication_name__id=med_id,
        )

        # We take the formulation ids and transform them to use like filter
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
        if formulation_ids:
            provider_medication_qs = provider_medication_qs.filter(
                medication__id__in=formulation_ids,
            )

        # Now we check if there is a list of type of providers to filter
        provider_type_list = self.request.query_params.get(
            'provider_type',
            [],
        )
        if provider_type_list:
            provider_type_list = provider_type_list.split(',')
            provider_medication_qs = provider_medication_qs.filter(
                provider__type__in=provider_type_list,
            )

        # Annotate the list of the medication levels for every county
        # to be used to calculate the low/medium/high after in the serializer
        # We create a list of the ids of the provider medication objects that
        # we have after filtering.
        provider_medication_ids = provider_medication_qs.values_list(
            'id',
            flat=True,
        )
        qs = County.objects.filter(
            state__id=state,
        ).select_related(
            'state',
        ).annotate(
            medication_levels=ArrayAgg(
                'county_zipcodes__providers__provider_medication__level',
                filter=Q(
                        county_zipcodes__providers__provider_medication__id__in=provider_medication_ids # noqa
                )
            ),
            centroid=AsGeoJSON(Centroid('state__geometry')),
        )
        return qs


class GeoZipCodeWithMedicationsView(RetrieveAPIView):
    serializer_class = GeoZipCodeWithMedicationsSerializer
    permission_classes = (IsAuthenticated,)
    lookup_field = 'zipcode'

    def get_queryset(self):
        med_id = self.request.query_params.get('med_id')
        zipcode = self.kwargs.get('zipcode')
        try:
            if not med_id or int(
                med_id
            ) not in MedicationName.objects.values_list(
                'id',
                flat=True,
            ):
                return ZipCode.objects.none()
        except ValueError:
            return ZipCode.objects.none()

        # First we take list of provider medication for this med, we will
        # use it for future filters
        provider_medication_qs = ProviderMedicationThrough.objects.filter(
            latest=True,
            medication__medication_name__id=med_id,
        )

        # We take the formulation ids and transform them to use like filter
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
        if formulation_ids:
            provider_medication_qs = provider_medication_qs.filter(
                medication__id__in=formulation_ids,
            )

        # Now we check if there is a list of type of providers to filter
        provider_type_list = self.request.query_params.get(
            'provider_type',
            [],
        )
        if provider_type_list:
            provider_type_list = provider_type_list.split(',')
            provider_medication_qs = provider_medication_qs.filter(
                provider__type__in=provider_type_list,
            )

        # We create a list of the ids of the provider medication objects that
        # we have after filtering.
        provider_medication_ids = provider_medication_qs.values_list(
            'id',
            flat=True,
        )
        zipcode_qs = ZipCode.objects.filter(zipcode=zipcode).annotate(
            medication_levels=ArrayAgg(
                'providers__provider_medication__level',
                filter=Q(
                        providers__provider_medication__id__in=provider_medication_ids # noqa
                )
            ),
            centroid=AsGeoJSON(Centroid('geometry')),
        )
        return zipcode_qs


class ProviderTypesView(ListAPIView):
    serializer_class = ProviderTypesSerializer
    permission_classes = (IsAuthenticated,)
    allowed_methods = ['GET']

    def get_queryset(self):
        med_id = self.request.query_params.get('med_id')
        state_id = self.request.query_params.get('state_id')
        zipcode = self.request.query_params.get('zipcode')
        try:
            if not med_id or int(
                med_id
            ) not in MedicationName.objects.values_list(
                'id',
                flat=True,
            ):
                return None
        except ValueError:
            return None

        provider_medication_qs = ProviderMedicationThrough.objects.filter(
            latest=True,
            medication__medication_name__id=med_id,
        )

        if state_id and not zipcode:
            # If we have zipcode we dont take into account the state
            try:
                provider_medication_qs = provider_medication_qs.filter(
                    provider__related_zipcode__state__id=int(state_id),
                )
            except ValueError:
                pass

        if zipcode:
            provider_medication_qs = provider_medication_qs.filter(
                provider__zip=zipcode,
            )

        # We take the formulation ids and transform them to use like filter
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
        if formulation_ids:
            provider_medication_qs = provider_medication_qs.filter(
                medication__id__in=formulation_ids,
            )

        provider_medication_ids = provider_medication_qs.values_list(
            'id',
            flat=True,
        )
        return Provider.objects.filter(
            provider_medication__id__in=provider_medication_ids
        ).values('type').annotate(Count('type'))

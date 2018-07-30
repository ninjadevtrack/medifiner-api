from django.db.models import Q
from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.gis.db.models.functions import Centroid, AsGeoJSON

from django.utils.translation import ugettext_lazy as _

from rest_framework import status, viewsets
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from medications.tasks import generate_medications
from .serializers import (
    CSVUploadSerializer,
    MedicationNameSerializer,
    StateSerializer,
    GeoStateWithMedicationsSerializer,
    GeoCountyWithMedicationsSerializer,
)
from .models import (
    County,
    TemporaryFile,
    MedicationName,
    State,
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
        if not med_id:
            return State.objects.none()
        # Annotate the list of the medication levels for every state
        # to be used to calculate the low/medium/high after in the serializer
        qs = State.objects.all().annotate(
            medication_levels=ArrayAgg(
                'zipcodes__providers__provider_medication__level',
                filter=Q(
                        zipcodes__providers__provider_medication__medication__medication_name__id=med_id, #noqa
                        zipcodes__providers__provider_medication__latest=True,
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
        if not med_id or not state:
            return County.objects.none()
        # Annotate the list of the medication levels for every county
        # to be used to calculate the low/medium/high after in the serializer
        qs = County.objects.filter(
            state__id=state,
        ).select_related(
            'state',
        ).annotate(
            medication_levels=ArrayAgg( # TODO: relation without state once county/zipcode relation is made
                'state__zipcodes__providers__provider_medication__level',
                filter=Q(
                        state__zipcodes__providers__provider_medication__medication__medication_name__id=med_id, #noqa
                        state__zipcodes__providers__provider_medication__latest=True, #noqa
                )
            ),
            centroid=AsGeoJSON(Centroid('state__geometry')),
        )
        return qs

#TODO view for zipcode selected

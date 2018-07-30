from django.db.models import Prefetch, Subquery, OuterRef, Q
from django.contrib.postgres.aggregates import ArrayAgg
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
)
from .models import (
    TemporaryFile,
    MedicationName,
    State,
    ProviderMedicationThrough,
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
    queryset = State.objects.all()


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
            )
        )
        return qs


#TODO: same view that state but for counties

#TODO view for zipcode selected

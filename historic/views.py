from django.db.models import Q, Prefetch

from rest_framework.generics import (
    ListAPIView,
)
from rest_framework.permissions import IsAuthenticated, AllowAny

from medications.models import (
    Medication,
    MedicationName,
    ProviderMedicationThrough,
)
from .serializers import AverageSupplyLevelSerializer


class HistoricAverageNationalLevelView(ListAPIView):
    serializer_class = AverageSupplyLevelSerializer
    permission_classes = (IsAuthenticated,) 
    allowed_methods = ['GET']

    def get_queryset(self):
        med_id = self.request.query_params.get('med_id')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        try:
            if not med_id or int(
                med_id
            ) not in MedicationName.objects.values_list(
                'id',
                flat=True,
            ):
                return Medication.objects.none()
        except ValueError:
            return Medication.objects.none()

        if not (start_date and end_date):
            return Medication.objects.none()

        # First we take list of provider medication for this med, we will
        # use it for future filters
        provider_medication_qs = ProviderMedicationThrough.objects.filter(
            medication__medication_name__id=med_id,
        )

        # Now we check if there is a list of type of providers to filter
        provider_type_list = self.request.query_params.get(
            'provider_type',
            [],
        )
        if provider_type_list:
            try:
                provider_type_list = provider_type_list.split(',')
                provider_medication_qs = provider_medication_qs.filter(
                    provider__type__in=provider_type_list,
                )
            except ValueError:
                pass

        # Now we check if there is a list of category of providers to filter
        provider_category_list = self.request.query_params.get(
            'provider_category',
            [],
        )
        if provider_category_list:
            try:
                provider_category_list = provider_category_list.split(',')
                provider_medication_qs = provider_medication_qs.filter(
                    provider__category__in=provider_category_list,
                )
            except ValueError:
                pass

        # Now we check if there is a list of drug types to filter
        drug_type_list = self.request.query_params.get(
            'drug_type',
            [],
        )
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
        qs = Medication.objects.filter(
            provider_medication__id__in=provider_medication_ids,
        ).prefetch_related(
            Prefetch(
                'provider_medication',
                queryset=ProviderMedicationThrough.objects.filter(
                    date__range=[start_date, end_date],
                )
            )
        )
        return qs


class HistoricAverageStateLevelView(ListAPIView):
    serializer_class = AverageSupplyLevelSerializer
    permission_classes = (IsAuthenticated,)
    allowed_methods = ['GET']

    def get_queryset(self):
        state_id = self.kwargs.get('state_id')
        med_id = self.request.query_params.get('med_id')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        try:
            if not med_id or int(
                med_id
            ) not in MedicationName.objects.values_list(
                'id',
                flat=True,
            ):
                return Medication.objects.none()
        except ValueError:
            return Medication.objects.none()

        if not (start_date and end_date):
            return Medication.objects.none()

        # First we take list of provider medication for this med, we will
        # use it for future filters
        provider_medication_qs = ProviderMedicationThrough.objects.filter(
            medication__medication_name__id=med_id,
            provider__related_zipcode__state=state_id,
        )

        # Now we check if there is a list of type of providers to filter
        provider_type_list = self.request.query_params.get(
            'provider_type',
            [],
        )
        if provider_type_list:
            try:
                provider_type_list = provider_type_list.split(',')
                provider_medication_qs = provider_medication_qs.filter(
                    provider__type__in=provider_type_list,
                )
            except ValueError:
                pass

        # Now we check if there is a list of category of providers to filter
        provider_category_list = self.request.query_params.get(
            'provider_category',
            [],
        )
        if provider_category_list:
            try:
                provider_category_list = provider_category_list.split(',')
                provider_medication_qs = provider_medication_qs.filter(
                    provider__category__in=provider_category_list,
                )
            except ValueError:
                pass

        # Now we check if there is a list of drug types to filter
        drug_type_list = self.request.query_params.get(
            'drug_type',
            [],
        )
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
        qs = Medication.objects.filter(
            provider_medication__id__in=provider_medication_ids,
        ).prefetch_related(
            Prefetch(
                'provider_medication',
                queryset=ProviderMedicationThrough.objects.filter(
                    date__range=[start_date, end_date],
                )
            )
        )
        return qs


class HistoricAverageZipCodeLevelView(ListAPIView):
    serializer_class = AverageSupplyLevelSerializer
    permission_classes = (AllowAny,)
    allowed_methods = ['GET']
    lookup_field = 'zipcode'

    def get_queryset(self):
        zipcode = self.kwargs.get('zipcode')
        med_id = self.request.query_params.get('med_id')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        try:
            if not med_id or int(
                med_id
            ) not in MedicationName.objects.values_list(
                'id',
                flat=True,
            ):
                return Medication.objects.none()
        except ValueError:
            return Medication.objects.none()

        if not (start_date and end_date):
            return Medication.objects.none()

        # First we take list of provider medication for this med, we will
        # use it for future filters
        provider_medication_qs = ProviderMedicationThrough.objects.filter(
            medication__medication_name__id=med_id,
            provider__related_zipcode__zipcode=zipcode,
        )

        # Now we check if there is a list of type of providers to filter
        provider_type_list = self.request.query_params.get(
            'provider_type',
            [],
        )
        if provider_type_list:
            try:
                provider_type_list = provider_type_list.split(',')
                provider_medication_qs = provider_medication_qs.filter(
                    provider__type__in=provider_type_list,
                )
            except ValueError:
                pass

        # Now we check if there is a list of category of providers to filter
        provider_category_list = self.request.query_params.get(
            'provider_category',
            [],
        )
        if provider_category_list:
            try:
                provider_category_list = provider_category_list.split(',')
                provider_medication_qs = provider_medication_qs.filter(
                    provider__category__in=provider_category_list,
                )
            except ValueError:
                pass

        # Now we check if there is a list of drug types to filter
        drug_type_list = self.request.query_params.get(
            'drug_type',
            [],
        )
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
        qs = Medication.objects.filter(
            provider_medication__id__in=provider_medication_ids,
        ).prefetch_related(
            Prefetch(
                'provider_medication',
                queryset=ProviderMedicationThrough.objects.filter(
                    date__range=[start_date, end_date],
                )
            )
        )
        return qs

from datetime import datetime, timedelta

from django.db.models import Prefetch

from rest_framework.generics import (
    ListAPIView,
)
from rest_framework.permissions import IsAuthenticated

from medications.models import (
    Medication,
    MedicationName,
    ProviderMedicationThrough,
)
from .serializers import (
    AverageSupplyLevelSerializer,
    AverageSupplyLevelZipCodeSerializer,
    OverallSupplyLevelSerializer,
    OverallSupplyLevelZipCodeSerializer,
)


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

        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')

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
                    date__gte=start_date,
                    date__lte=end_date + timedelta(days=1),
                    # We add 1 day cause we want to check the medications
                    # supplies in end_date until 23:59:59 which in practice
                    # is next day 00:00:00
                )
            )
        ).distinct()
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

        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')

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
                    date__gte=start_date,
                    date__lte=end_date + timedelta(days=1),
                )
            )
        ).distinct()
        return qs


class HistoricAverageZipCodeLevelView(ListAPIView):
    serializer_class = AverageSupplyLevelZipCodeSerializer
    permission_classes = (IsAuthenticated,)
    allowed_methods = ['GET']
    lookup_field = 'zipcode'

    def get_queryset(self):
        zipcode = self.kwargs.get('zipcode')
        self.request.data['zipcode'] = zipcode
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

        start_date = datetime.strptime(start_date, '%Y-%m-%d').astimezone()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').astimezone()

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
                    date__gte=start_date,
                    date__lte=end_date + timedelta(days=1),
                )
            )
        ).distinct()
        return qs


class HistoricOverallNationalLevelView(ListAPIView):
    serializer_class = OverallSupplyLevelSerializer
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
                return MedicationName.objects.none()
        except ValueError:
            return MedicationName.objects.none()
        if not (start_date and end_date):
            return MedicationName.objects.none()

        start_date = datetime.strptime(start_date, '%Y-%m-%d').astimezone()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').astimezone()

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
        qs = MedicationName.objects.filter(
            id=med_id,
        ).prefetch_related(
            Prefetch(
                'medications',
                queryset=Medication.objects.filter(
                    provider_medication__id__in=provider_medication_ids,
                ).prefetch_related(
                    Prefetch(
                        'provider_medication',
                        queryset=ProviderMedicationThrough.objects.filter(
                            date__gte=start_date,
                            date__lte=end_date + timedelta(days=1),
                        )
                    )
                ).distinct()
            ),
        )

        return qs


class HistoricOverallStateLevelView(ListAPIView):
    serializer_class = OverallSupplyLevelSerializer
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
                return MedicationName.objects.none()
        except ValueError:
            return MedicationName.objects.none()
        if not (start_date and end_date):
            return MedicationName.objects.none()

        start_date = datetime.strptime(start_date, '%Y-%m-%d').astimezone()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').astimezone()

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
        qs = MedicationName.objects.filter(
            id=med_id,
        ).prefetch_related(
            Prefetch(
                'medications',
                queryset=Medication.objects.filter(
                    provider_medication__id__in=provider_medication_ids,
                ).prefetch_related(
                    Prefetch(
                        'provider_medication',
                        queryset=ProviderMedicationThrough.objects.filter(
                            id__in=provider_medication_ids,
                            date__gte=start_date,
                            date__lte=end_date + timedelta(days=1),
                        )
                    )
                ).distinct()
            ),
        )
        return qs


class HistoricOverallZipCodeLevelView(ListAPIView):
    serializer_class = OverallSupplyLevelZipCodeSerializer
    permission_classes = (IsAuthenticated,)
    allowed_methods = ['GET']
    lookup_field = 'zipcode'

    def get_queryset(self):
        zipcode = self.kwargs.get('zipcode')
        self.request.data['zipcode'] = zipcode
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
                return MedicationName.objects.none()
        except ValueError:
            return MedicationName.objects.none()
        if not (start_date and end_date):
            return MedicationName.objects.none()

        start_date = datetime.strptime(start_date, '%Y-%m-%d').astimezone()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').astimezone()

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
        qs = MedicationName.objects.filter(
            id=med_id,
        ).prefetch_related(
            Prefetch(
                'medications',
                queryset=Medication.objects.filter(
                    provider_medication__id__in=provider_medication_ids,
                ).prefetch_related(
                    Prefetch(
                        'provider_medication',
                        queryset=ProviderMedicationThrough.objects.filter(
                            id__in=provider_medication_ids,
                            date__gte=start_date,
                            date__lte=end_date + timedelta(days=1),
                        )
                    )
                ).distinct()
            ),
        )

        return qs

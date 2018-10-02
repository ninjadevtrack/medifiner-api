from datetime import datetime, timedelta

from django.db.models import Prefetch
from django.utils.translation import ugettext_lazy as _

from rest_registration.exceptions import BadRequest

from rest_framework.generics import (
    ListAPIView,
)
from rest_framework.permissions import IsAuthenticated

from medications.models import (
    Medication,
    MedicationName,
    ProviderMedicationNdcThrough,
)
from .serializers import (
    AverageSupplyLevelSerializer,
    AverageSupplyLevelZipCodeSerializer,
    OverallSupplyLevelSerializer,
    OverallSupplyLevelZipCodeSerializer,
)


def get_provider_medication_queryset(query_params, state_id=None, zipcode=None):
    med_id = query_params.get('med_id')

    # First we take list of provider medication for this med, we will
    # use it for future filter
    if zipcode:
        provider_medication_qs = ProviderMedicationNdcThrough.objects.filter(
            medication_ndc__medication__medication_name__id=med_id,
            provider__related_zipcode__zipcode=zipcode,
        )
    elif state_id:
        provider_medication_qs = ProviderMedicationNdcThrough.objects.filter(
            medication_ndc__medication__medication_name__id=med_id,
            provider__related_zipcode__state=state_id,
        )
    else:
        provider_medication_qs = ProviderMedicationNdcThrough.objects.filter(
            medication_ndc__medication__medication_name__id=med_id,
        )

    # Now we check if there is a list of type of providers to filter
    provider_type_list = query_params.get(
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
    provider_category_list = query_params.get(
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
    formulation_ids_raw = query_params.get(
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
            medication_ndc__medication__id__in=formulation_ids,
        )

    # Now we check if there is a list of drug types to filter
    drug_type_list = query_params.get(
        'drug_type',
        [],
    )
    if drug_type_list:
        try:
            drug_type_list = drug_type_list.split(',')
            provider_medication_qs = provider_medication_qs.filter(
                medication_ndc__medication__drug_type__in=drug_type_list,
            )
        except ValueError:
            pass

    provider_medication_ids = provider_medication_qs.values_list(
        'id',
        flat=True,
    )
    return provider_medication_ids


class HistoricAverageNationalLevelView(ListAPIView):
    serializer_class = AverageSupplyLevelSerializer
    permission_classes = (IsAuthenticated,)
    allowed_methods = ['GET']

    def get_queryset(self):
        '''
        query_params:
            - med_id: MedicationName id
            - start_date: Date str to start filter
            - end_date: Date str to end filter
            - formulations: list of Medication ids
            - provider_category: list of ProviderCategory ids
            - provider_type: list of ProviderType ids
            - drug_type: list of 1 character str, for drug_type in Medication
        '''
        med_id = self.request.query_params.get('med_id')
        query_params = self.request.query_params
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
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').astimezone()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').astimezone()
        except ValueError as e:
            raise BadRequest(_('Incorrect date: {}').format(e))
        provider_medication_ids = get_provider_medication_queryset(
            query_params,
        )
        qs = Medication.objects.filter(
            ndc_codes__provider_medication__id__in=provider_medication_ids,
        ).prefetch_related(
            Prefetch(
                'ndc_codes__provider_medication',
                queryset=ProviderMedicationNdcThrough.objects.filter(
                    creation_date__gte=start_date,
                    creation_date__lte=end_date + timedelta(days=1),
                    # We add 1 day cause we want to check the medications
                    # supplies in end_date until 23:59:59 which in practice
                    # is next day 00:00:00
                ),
            )
        ).distinct()
        return qs


class HistoricAverageStateLevelView(ListAPIView):
    serializer_class = AverageSupplyLevelSerializer
    permission_classes = (IsAuthenticated,)
    allowed_methods = ['GET']

    def get_queryset(self):
        '''
        kwargs: state_id

        query_params:
            - med_id: MedicationName id
            - start_date: Date str to start filter
            - end_date: Date str to end filter
            - formulations: list of Medication ids
            - provider_category: list of ProviderCategory ids
            - provider_type: list of ProviderType ids
            - drug_type: list of 1 character str, for drug_type in Medication
        '''
        state_id = self.kwargs.get('state_id')
        query_params = self.request.query_params
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

        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').astimezone()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').astimezone()
        except ValueError as e:
            raise BadRequest(_('Incorrect date: {}').format(e))

        provider_medication_ids = get_provider_medication_queryset(
            query_params,
            state_id=state_id,
        )
        qs = Medication.objects.filter(
            ndc_codes__provider_medication__id__in=provider_medication_ids,
        ).prefetch_related(
            Prefetch(
                'ndc_codes__provider_medication',
                queryset=ProviderMedicationNdcThrough.objects.filter(
                    creation_date__gte=start_date,
                    creation_date__lte=end_date + timedelta(days=1),
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
        '''
        kwargs: zipcode

        query_params:
            - med_id: MedicationName id
            - start_date: Date str to start filter
            - end_date: Date str to end filter
            - formulations: list of Medication ids
            - provider_category: list of ProviderCategory ids
            - provider_type: list of ProviderType ids
            - drug_type: list of 1 character str, for drug_type in Medication
        '''
        zipcode = self.kwargs.get('zipcode')
        self.request.data['zipcode'] = zipcode
        med_id = self.request.query_params.get('med_id')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        query_params = self.request.query_params

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

        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').astimezone()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').astimezone()
        except ValueError as e:
            raise BadRequest(_('Incorrect date: {}').format(e))

        provider_medication_ids = get_provider_medication_queryset(
            query_params,
            zipcode=zipcode,
        )
        qs = Medication.objects.filter(
            ndc_codes__provider_medication__id__in=provider_medication_ids,
        ).prefetch_related(
            Prefetch(
                'ndc_codes__provider_medication',
                queryset=ProviderMedicationNdcThrough.objects.filter(
                    creation_date__gte=start_date,
                    creation_date__lte=end_date + timedelta(days=1),
                )
            )
        ).distinct()
        return qs


class HistoricOverallNationalLevelView(ListAPIView):
    serializer_class = OverallSupplyLevelSerializer
    permission_classes = (IsAuthenticated,)
    allowed_methods = ['GET']

    def get_queryset(self):
        '''
        query_params:
            - med_id: MedicationName id
            - start_date: Date str to start filter
            - end_date: Date str to end filter
            - formulations: list of Medication ids
            - provider_category: list of ProviderCategory ids
            - provider_type: list of ProviderType ids
            - drug_type: list of 1 character str, for drug_type in Medication
        '''
        query_params = self.request.query_params
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

        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').astimezone()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').astimezone()
        except ValueError as e:
            raise BadRequest(_('Incorrect date: {}').format(e))

        provider_medication_ids = get_provider_medication_queryset(
            query_params,
        )

        qs = MedicationName.objects.filter(
            id=med_id,
        ).prefetch_related(
            Prefetch(
                'medications',
                queryset=Medication.objects.filter(
                    ndc_codes__provider_medication__id__in=provider_medication_ids, # noqa
                ).prefetch_related(
                    Prefetch(
                        'ndc_codes__provider_medication',
                        queryset=ProviderMedicationNdcThrough.objects.filter(
                            creation_date__gte=start_date,
                            creation_date__lte=end_date + timedelta(days=1),
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
        '''
        kwargs: state_id

        query_params:
            - med_id: MedicationName id
            - start_date: Date str to start filter
            - end_date: Date str to end filter
            - formulations: list of Medication ids
            - provider_category: list of ProviderCategory ids
            - provider_type: list of ProviderType ids
            - drug_type: list of 1 character str, for drug_type in Medication
        '''
        state_id = self.kwargs.get('state_id')
        query_params = self.request.query_params
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

        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').astimezone()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').astimezone()
        except ValueError as e:
            raise BadRequest(_('Incorrect date: {}').format(e))

        provider_medication_ids = get_provider_medication_queryset(
            query_params,
            state_id=state_id,
        )
        qs = MedicationName.objects.filter(
            id=med_id,
        ).prefetch_related(
            Prefetch(
                'medications',
                queryset=Medication.objects.filter(
                    ndc_codes__provider_medication__id__in=provider_medication_ids, # noqa
                ).prefetch_related(
                    Prefetch(
                        'ndc_codes__provider_medication',
                        queryset=ProviderMedicationNdcThrough.objects.filter(
                            id__in=provider_medication_ids,
                            creation_date__gte=start_date,
                            creation_date__lte=end_date + timedelta(days=1),
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
        '''
        kwargs: zipcode

        query_params:
            - med_id: MedicationName id
            - start_date: Date str to start filter
            - end_date: Date str to end filter
            - formulations: list of Medication ids
            - provider_category: list of ProviderCategory ids
            - provider_type: list of ProviderType ids
            - drug_type: list of 1 character str, for drug_type in Medication
        '''
        zipcode = self.kwargs.get('zipcode')
        self.request.data['zipcode'] = zipcode
        query_params = self.request.query_params
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

        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').astimezone()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').astimezone()
        except ValueError as e:
            raise BadRequest(_('Incorrect date: {}').format(e))

        provider_medication_ids = get_provider_medication_queryset(
            query_params,
            zipcode=zipcode,
        )

        qs = MedicationName.objects.filter(
            id=med_id,
        ).prefetch_related(
            Prefetch(
                'medications',
                queryset=Medication.objects.filter(
                    ndc_codes__provider_medication__id__in=provider_medication_ids, # noqa
                ).prefetch_related(
                    Prefetch(
                        'ndc_codes__provider_medication',
                        queryset=ProviderMedicationNdcThrough.objects.filter(
                            id__in=provider_medication_ids,
                            creation_date__gte=start_date,
                            creation_date__lte=end_date + timedelta(days=1),
                        )
                    )
                ).distinct()
            ),
        )

        return qs

from datetime import datetime, timedelta

from django.db.models import Count, DateField
from rest_framework.response import Response
from django.utils.translation import ugettext_lazy as _

from django.db.models.functions import Cast

from rest_registration.exceptions import BadRequest

from rest_framework.views import APIView

from rest_framework.permissions import IsAuthenticated

from medications.models import (
    MedicationName,
    MedicationNdc,
    Provider,
    ProviderMedicationNdcThrough,
    State,
    ZipCode,
)
from .serializers import (
    AverageSupplyLevelSerializer,
    OverallSupplyLevelSerializer,
)


def get_medication_ndc_ids(query_params):
    med_id = query_params.get('med_id')

    medication_nds_qs = MedicationNdc.objects.all()

    if med_id:
        medication_nds_qs = medication_nds_qs.filter(
            medication__medication_name__id=med_id,
        )

    # We take the formulation ids and transform them to use like filter
    formulation_ids_raw = query_params.get(
        'formulations',
    )
    if not formulation_ids_raw and formulation_ids_raw is not None:
        # Catch the case when in url we have &formulations=
        # meaning the user unchecked all formulations
        return ProviderMedicationNdcThrough.objects.none()
    formulation_ids = []
    if formulation_ids_raw:
        try:
            formulation_ids = list(
                map(int, formulation_ids_raw.split(','))
            )
        except ValueError:
            pass
    if formulation_ids:
        medication_nds_qs = medication_nds_qs.filter(
            medication__id__in=formulation_ids,
        )

    # Now we check if there is a list of drug types to filter
    drug_type_list = query_params.get(
        'drug_type',
        [],
    )
    if drug_type_list:
        try:
            drug_type_list = drug_type_list.split(',')
            medication_nds_qs = medication_nds_qs.filter(
                medication__drug_type__in=drug_type_list,
            )
        except ValueError:
            pass

    return medication_nds_qs.values_list(
        'id',
        flat=True,
    )


def get_provider_ids(query_params, state_id=None, zipcode=None):
    if zipcode:
        provider_qs = Provider.objects.filter(
            related_zipcode__zipcode=zipcode,
        )
    elif state_id:
        provider_qs = Provider.objects.filter(
            related_zipcode__state=state_id,
        )
    else:
        provider_qs = Provider.objects.all()

    # Now we check if there is a list of type of providers to filter
    provider_type_list = query_params.get(
        'provider_type',
        [],
    )
    if provider_type_list:
        try:
            provider_type_list = provider_type_list.split(',')
            provider_qs = provider_qs.filter(
                type__in=provider_type_list,
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
            provider_qs = provider_qs.filter(
                category__in=provider_category_list,
            )
        except ValueError:
            pass

    return provider_qs.values_list(
        'id',
        flat=True,
    )


class HistoricAverageNationalLevelView(APIView):
    permission_classes = (IsAuthenticated,)
    allowed_methods = ['GET']

    def get(self, request):
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
        med_id = request.query_params.get('med_id')
        query_params = request.query_params
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        try:
            if not med_id or int(
                med_id
            ) not in MedicationName.objects.values_list(
                'id',
                flat=True,
            ):
                raise BadRequest(_('Wrong med_id in the request.'))
        except ValueError:
            raise BadRequest(_('Wrong med_id in the request.'))

        if not (start_date and end_date):
            raise BadRequest(_('You must provide start_date and end_date.'))
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').astimezone()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').astimezone()
        except ValueError as e:
            raise BadRequest(_('Incorrect date: {}').format(e))

        if end_date <= start_date:
            raise BadRequest(_('start_date must precede end_date.'))

        # 1 - Find list of medication_ndc_ids
        medication_ndc_ids = get_medication_ndc_ids(query_params)

        # 2 - Find list of provider_ids
        provider_ids = get_provider_ids(query_params)

        # 3 - Query ProviderMedicationNdcThrough
        # to find count of supply levels per date
        provider_medication_ndcs = ProviderMedicationNdcThrough.objects.filter(
            medication_ndc_id__in=medication_ndc_ids,
            provider_id__in=provider_ids,
            creation_date__gte=start_date,
            creation_date__lte=end_date + timedelta(days=1),
        ).distinct(
        ).values(
            'medication_ndc_id', 'level'
        ).annotate(
            count_for_level=Count('level'),
            creation_date_only=Cast('creation_date', DateField())
        ).order_by('creation_date_only')

        medication_ndcs = MedicationNdc.objects.filter(
            id__in=medication_ndc_ids
        ).values(
            'id',
            'medication__name',
        )

        context = {'request': request}
        data = AverageSupplyLevelSerializer(
            context=context).to_representation(
            medication_ndcs,
            provider_medication_ndcs,
        )
        return Response({"medication_supplies": data})


class HistoricAverageStateLevelView(APIView):
    permission_classes = (IsAuthenticated,)
    allowed_methods = ['GET']

    def get(self, request, state_id=None):
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
        if not state_id:
            raise BadRequest(_('No state_id in the request'))
        try:
                State.objects.get(id=state_id)
        except State.DoesNotExist:
            raise BadRequest(_('The state_id in the request does not exist'))

        med_id = request.query_params.get('med_id')
        query_params = request.query_params
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        try:
            if not med_id or int(
                med_id
            ) not in MedicationName.objects.values_list(
                'id',
                flat=True,
            ):
                raise BadRequest(_('Wrong med_id in the request.'))
        except ValueError:
            raise BadRequest(_('Wrong med_id in the request.'))

        if not (start_date and end_date):
            raise BadRequest(_('You must provide start_date and end_date.'))
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').astimezone()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').astimezone()
        except ValueError as e:
            raise BadRequest(_('Incorrect date: {}').format(e))

        if end_date <= start_date:
            raise BadRequest(_('start_date must precede end_date.'))

        # 1 - Find list of medication_ndc_ids
        medication_ndc_ids = get_medication_ndc_ids(query_params)

        # 2 - Find list of provider_ids
        provider_ids = get_provider_ids(query_params, state_id=state_id)

        # 3 - Query ProviderMedicationNdcThrough
        # to find count of supply levels per date
        provider_medication_ndcs = ProviderMedicationNdcThrough.objects.filter(
            medication_ndc_id__in=medication_ndc_ids,
            provider_id__in=provider_ids,
            creation_date__gte=start_date,
            creation_date__lte=end_date + timedelta(days=1),
        ).distinct(
        ).values(
            'medication_ndc_id', 'level'
        ).annotate(
            count_for_level=Count('level'),
            creation_date_only=Cast('creation_date', DateField())
        ).order_by('creation_date_only')

        medication_ndcs = MedicationNdc.objects.filter(
            id__in=medication_ndc_ids
        ).values(
            'id',
            'medication__name',
        )

        context = {'request': request}
        data = AverageSupplyLevelSerializer(
            context=context).to_representation(
            medication_ndcs,
            provider_medication_ndcs,
        )
        return Response({"medication_supplies": data})


class HistoricAverageZipCodeLevelView(APIView):
    permission_classes = (IsAuthenticated,)
    allowed_methods = ['GET']
    lookup_field = 'zipcode'

    def get(self, request, zipcode=None):
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
        if not zipcode:
            raise BadRequest(_('No zipcode in the request.'))
        try:
                ZipCode.objects.get(zipcode=zipcode)
        except ZipCode.DoesNotExist:
            raise BadRequest(_('The zipcode in the request does not exist.'))

        med_id = request.query_params.get('med_id')
        query_params = request.query_params
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        try:
            if not med_id or int(
                med_id
            ) not in MedicationName.objects.values_list(
                'id',
                flat=True,
            ):
                raise BadRequest(_('Wrong med_id in the request'))
        except ValueError:
            raise BadRequest(_('Wrong med_id in the request'))

        if not (start_date and end_date):
            raise BadRequest(_('You must provide start_date and end_date.'))
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').astimezone()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').astimezone()
        except ValueError as e:
            raise BadRequest(_('Incorrect date: {}').format(e))

        if end_date <= start_date:
            raise BadRequest(_('start_date must precede end_date.'))

        # 1 - Find list of medication_ndc_ids
        medication_ndc_ids = get_medication_ndc_ids(query_params)

        # 2 - Find list of provider_ids
        provider_ids = get_provider_ids(query_params, zipcode=zipcode)

        # 3 - Query ProviderMedicationNdcThrough
        # to find count of supply levels per date
        provider_medication_ndcs = ProviderMedicationNdcThrough.objects.filter(
            medication_ndc_id__in=medication_ndc_ids,
            provider_id__in=provider_ids,
            creation_date__gte=start_date,
            creation_date__lte=end_date + timedelta(days=1),
        ).distinct(
        ).values(
            'medication_ndc_id', 'level'
        ).annotate(
            count_for_level=Count('level'),
            creation_date_only=Cast('creation_date', DateField())
        ).order_by('creation_date_only')

        medication_ndcs = MedicationNdc.objects.filter(
            id__in=medication_ndc_ids
        ).values(
            'id',
            'medication__name',
        )

        context = {'request': request}
        data = AverageSupplyLevelSerializer(
            context=context).to_representation(
            medication_ndcs,
            provider_medication_ndcs,
        )
        return Response({"medication_supplies": data})


class HistoricOverallNationalLevelView(APIView):
    permission_classes = (IsAuthenticated,)
    allowed_methods = ['GET']

    def get(self, request):
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
                raise BadRequest(_('Wrong med_id in the request.'))
        except ValueError:
            raise BadRequest(_('Wrong med_id in the request.'))

        if not (start_date and end_date):
            raise BadRequest(_('You must provide start_date and end_date.'))
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').astimezone()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').astimezone()
        except ValueError as e:
            raise BadRequest(_('Incorrect date: {}').format(e))

        if end_date <= start_date:
            raise BadRequest(_('start_date must precede end_date.'))

        # 1 - Find list of medication_ndc_ids
        medication_ndc_ids = get_medication_ndc_ids(query_params)

        # 2 - Find list of provider_ids
        provider_ids = get_provider_ids(query_params)

        # 3 - Query ProviderMedicationNdcThrough to
        # find count of supply levels per date
        provider_medication_ndcs = ProviderMedicationNdcThrough.objects.filter(
            medication_ndc_id__in=medication_ndc_ids,
            provider_id__in=provider_ids,
            creation_date__gte=start_date,
            creation_date__lte=end_date + timedelta(days=1),
        ).distinct(
        ).values(
            'level'
        ).annotate(
            count_for_level=Count('level'),
            creation_date_only=Cast('creation_date', DateField())
        ).order_by('creation_date_only')

        context = {'request': request}
        data = OverallSupplyLevelSerializer(
            context=context).to_representation(provider_medication_ndcs)
        return Response(
            {"medication_supplies": [{'overall_supply_per_day': data}]}
        )


class HistoricOverallStateLevelView(APIView):
    permission_classes = (IsAuthenticated,)
    allowed_methods = ['GET']

    def get(self, request, state_id=None):
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
        if not state_id:
            raise BadRequest(_('No state_id in the request'))
        try:
                State.objects.get(id=state_id)
        except State.DoesNotExist:
            raise BadRequest(_('The state_id in the request does not exist'))

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
                raise BadRequest(_('Wrong med_id in the request.'))
        except ValueError:
            raise BadRequest(_('Wrong med_id in the request.'))

        if not (start_date and end_date):
            raise BadRequest(_('You must provide start_date and end_date.'))
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').astimezone()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').astimezone()
        except ValueError as e:
            raise BadRequest(_('Incorrect date: {}').format(e))

        if end_date <= start_date:
            raise BadRequest(_('start_date must precede end_date.'))

        # 1 - Find list of medication_ndc_ids
        medication_ndc_ids = get_medication_ndc_ids(query_params)

        # 2 - Find list of provider_ids
        provider_ids = get_provider_ids(query_params, state_id=state_id)

        # 3 - Query ProviderMedicationNdcThrough to
        # find count of supply levels per date
        provider_medication_ndcs = ProviderMedicationNdcThrough.objects.filter(
            medication_ndc_id__in=medication_ndc_ids,
            provider_id__in=provider_ids,
            creation_date__gte=start_date,
            creation_date__lte=end_date + timedelta(days=1),
        ).distinct(
        ).values(
            'level'
        ).annotate(
            count_for_level=Count('level'),
            creation_date_only=Cast('creation_date', DateField())
        ).order_by('creation_date_only')

        context = {'request': request}
        data = OverallSupplyLevelSerializer(
            context=context).to_representation(provider_medication_ndcs)
        return Response(
            {"medication_supplies": [{'overall_supply_per_day': data}]}
        )


class HistoricOverallZipCodeLevelView(APIView):
    permission_classes = (IsAuthenticated,)
    allowed_methods = ['GET']
    lookup_field = 'zipcode'

    def get(self, request, zipcode=None):
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
        if not zipcode:
            raise BadRequest(_('No zipcode in the request.'))
        try:
                ZipCode.objects.get(zipcode=zipcode)
        except ZipCode.DoesNotExist:
            raise BadRequest(_('The zipcode in the request does not exist.'))

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
                raise BadRequest(_('Wrong med_id in the request.'))
        except ValueError:
            raise BadRequest(_('Wrong med_id in the request.'))

        if not (start_date and end_date):
            raise BadRequest(_('You must provide start_date and end_date.'))
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').astimezone()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').astimezone()
        except ValueError as e:
            raise BadRequest(_('Incorrect date: {}').format(e))

        if end_date <= start_date:
            raise BadRequest(_('start_date must precede end_date.'))

        # 1 - Find list of medication_ndc_ids
        medication_ndc_ids = get_medication_ndc_ids(query_params)

        # 2 - Find list of provider_ids
        provider_ids = get_provider_ids(query_params, zipcode=zipcode)

        # 3 - Query ProviderMedicationNdcThrough to
        # find count of supply levels per date
        provider_medication_ndcs = ProviderMedicationNdcThrough.objects.filter(
            medication_ndc_id__in=medication_ndc_ids,
            provider_id__in=provider_ids,
            creation_date__gte=start_date,
            creation_date__lte=end_date + timedelta(days=1),
        ).distinct(
        ).values(
            'level'
        ).annotate(
            count_for_level=Count('level'),
            creation_date_only=Cast('creation_date', DateField())
        ).order_by('creation_date_only')

        context = {'request': request}
        data = OverallSupplyLevelSerializer(
            context=context).to_representation(provider_medication_ndcs)
        return Response(
            {"medication_supplies": [{'overall_supply_per_day': data}]}
        )

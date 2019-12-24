from datetime import datetime, timedelta

from django.db.models import Count, DateField
from django.db.models.functions import Cast
from django.utils.translation import ugettext_lazy as _

from rest_registration.exceptions import BadRequest
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from medications.models import (
    MedicationName,
    MedicationNdc,
    MedicationMedicationNameMedicationDosageThrough,
    Provider,
    ProviderMedicationNdcThrough,
    State,
    ZipCode,
)
from medications.utils import force_user_state_id_and_zipcode
from .serializers import (
    AverageSupplyLevelSerializer,
    OverallSupplyLevelSerializer,
)


#####################################################################################
###################################### Utils ########################################
#####################################################################################


def get_medication_ndc_ids(query_params):
    dosages = query_params.getlist('dosages[]', [])
    med_id = query_params.get('med_id')

    med_ndc_ids = MedicationMedicationNameMedicationDosageThrough.objects.filter(
        medication_name_id=med_id,
        medication_dosage_id__in=dosages
    ).select_related(
        'medication__ndc_codes',
    ).distinct().values_list('medication__ndc_codes', flat=True)

    return med_ndc_ids


def get_provider_ids(query_params, state_id=None, zipcode=None):
    provider_categories = query_params.getlist('provider_categories[]', [])
    provider_types = query_params.getlist('provider_types[]', [])

    provider_qs = Provider.objects.filter(
        category__in=provider_categories,
        type__in=provider_types,
    )

    if zipcode:
        provider_qs = provider_qs.filter(related_zipcode__zipcode=zipcode)

    if state_id:
        provider_qs = provider_qs.filter(related_zipcode__state=state_id)

    return provider_qs.values_list('id', flat=True)


def validate_dates(query_params):
    start_date = query_params.get('start_date')
    end_date = query_params.get('end_date')

    if not (start_date and end_date):
        raise BadRequest(_('start_date and end_date required'))
    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').astimezone()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').astimezone()
    except ValueError as e:
        raise BadRequest(_('Incorrect date: {}').format(e))

    if end_date <= start_date:
        raise BadRequest(_('start_date must precede end_date.'))

    return start_date, end_date


#####################################################################################
################################## HistoricAverage ##################################
#####################################################################################


class HistoricAverageView(APIView):
    permission_classes = (IsAuthenticated,)
    allowed_methods = ['GET']

    def dispatch(self, request, *args, **kwargs):
        '''
        kwargs: may be state_id or zipcode
        '''
        kwargs_keys = kwargs.keys()
        if 'state_id' in kwargs_keys:
            self.state_id = kwargs.pop('state_id')
        if 'zipcode' in kwargs_keys:
            self.zipcode = kwargs.pop('zipcode')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        '''
        query_params:
            - med_id: MedicationName id
            - start_date: Date str to start filter
            - end_date: Date str to end filter
            - dosages: list of Dosage ids
            - drug_type: list of 1 character str, for drug_type in Medication
            - provider_category: list of ProviderCategory ids
            - provider_type: list of ProviderType ids
            - state_id: State id
            - zipcode: ZipCode
        '''
        state_id = getattr(self, 'state_id', None)
        zipcode = getattr(self, 'zipcode', None)
        user = request.user

        # 1 - if state level user, ensure state id or zipcode
        state_id, zipcode = force_user_state_id_and_zipcode(
            user, state_id, zipcode)

        # 2 - validate dates
        start_date, end_date = validate_dates(request.query_params)

        # 3 - Find list of medication_ndc_ids
        medication_ndc_ids = get_medication_ndc_ids(request.query_params)

        # 4 - Find list of provider_ids
        provider_ids = get_provider_ids(
            request.query_params, state_id=state_id, zipcode=zipcode)

        # 5 - Query ProviderMedicationNdcThrough
        # to find count of supply levels per date
        provider_medication_ndcs = ProviderMedicationNdcThrough.objects.filter(
            medication_ndc_id__in=medication_ndc_ids,
            provider_id__in=provider_ids,
            date__gte=start_date,
            date__lte=end_date + timedelta(days=1),
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


#####################################################################################
################################## HistoricOverall ##################################
#####################################################################################

class HistoricOverallView(APIView):
    permission_classes = (IsAuthenticated,)
    allowed_methods = ['GET']

    def dispatch(self, request, *args, **kwargs):
        '''
        kwargs: may be state_id or zipcode
        '''
        kwargs_keys = kwargs.keys()
        if 'state_id' in kwargs_keys:
            self.state_id = kwargs.pop('state_id')
        if 'zipcode' in kwargs_keys:
            self.zipcode = kwargs.pop('zipcode')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        '''
        query_params:
            - med_id: MedicationName id
            - start_date: Date str to start filter
            - end_date: Date str to end filter
            - dosages: list of Dosage ids
            - drug_type: list of 1 character str, for drug_type in Medication
            - provider_category: list of ProviderCategory ids
            - provider_type: list of ProviderType ids
            - state_id: State id
            - zipcode: ZipCode
        '''
        state_id = getattr(self, 'state_id', None)
        user = request.user
        zipcode = getattr(self, 'zipcode', None)

        # 1 - block user access to state only if state level user
        state_id, zipcode = force_user_state_id_and_zipcode(
            user, state_id, zipcode)

        # 2 - validate dates
        start_date, end_date = validate_dates(self.request.query_params)

        # 3 - Find list of medication_ndc_ids
        medication_ndc_ids = get_medication_ndc_ids(self.request.query_params)

        # 4 - Find list of provider_ids
        provider_ids = get_provider_ids(
            self.request.query_params, state_id=state_id, zipcode=zipcode)

        # 5 - Query ProviderMedicationNdcThrough to
        # find count of supply levels per date
        provider_medication_ndcs = ProviderMedicationNdcThrough.objects.filter(
            medication_ndc_id__in=medication_ndc_ids,
            provider_id__in=provider_ids,
            date__gte=start_date,
            date__lte=end_date + timedelta(days=1),
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

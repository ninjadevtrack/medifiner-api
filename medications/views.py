import boto3
import botocore
import csv
import time

from datetime import datetime, timedelta

from django.conf import settings
from django.db.models import Q, Count, Prefetch
from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.gis.db.models.functions import Centroid, AsGeoJSON
from django.core.cache import cache
from django.core.exceptions import MultipleObjectsReturned

from django.utils.translation import ugettext_lazy as _

from rest_framework import status, viewsets, views
from rest_registration.exceptions import BadRequest
from rest_framework.response import Response
from rest_framework.generics import (
    GenericAPIView,
    ListAPIView,
    RetrieveAPIView,
)
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.http import HttpResponse

from epidemic.models import Epidemic
from medications.tasks import generate_medications, generate_csv_export
from .serializers import (
    CSVUploadSerializer,
    MedicationNameSerializer,
    StateSerializer,
    SimpleStateSerializer,
    GeoStateWithMedicationsSerializer,
    GeoCountyWithMedicationsSerializer,
    GeoZipCodeWithMedicationsSerializer,
    ProviderCategoriesSerializer,
    ProviderTypesSerializer,
    OrganizationSerializer,
)
from .models import (
    County,
    MedicationMedicationNameMedicationDosageThrough,
    MedicationName,
    MedicationNameEquivalence,
    MedicationType,
    MedicationTypeMedicationNameThrough,
    Organization,
    Provider,
    ProviderMedicationNdcThrough,
    ProviderType,
    ProviderCategory,
    State,
    ZipCode,
    Medication,
    MedicationNdc,
)

from .permissions import (
    NationalLevel,
    SelfStatePermissionLevel,
    SelfZipCodePermissionLevel,
)

from .utils import force_user_state_id_and_zipcode


class CSVUploadView(GenericAPIView):
    serializer_class = CSVUploadSerializer
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        csv_file = serializer.validated_data.pop('csv_file')
        organization_id = serializer.validated_data.pop('organization_id')
        import_date = serializer.validated_data.pop('import_date')
        cache_key = '{}_{}_{}'.format(
            csv_file.name, request.user.id, organization_id)
        cache.set(cache_key, csv_file, None)
        generate_medications.delay(
            cache_key,
            organization_id,
            request.user.email,
            import_date,
        )
        return Response(
            {'status': _('Supply level import process has been queued')},
            status=status.HTTP_200_OK,
        )


def medication_name_dosage_type_filters():
    medication_type_mapping = {}
    medication_name_mapping = {}
    med_type_med_name_data = {}

    for med in MedicationTypeMedicationNameThrough.objects.all().values(
        'medication_name_id',
        'medication_name__name',
        'medication_type__name',
        'medication_type_id',
    ):
        medication_name_mapping[med['medication_name_id']
                                ] = med['medication_name__name']
        medication_type_mapping[med['medication_type_id']
                                ] = med['medication_type__name']

        med_type_med_name_data[med['medication_name_id']] = {
        } if med['medication_name_id'] not in med_type_med_name_data else med_type_med_name_data[med['medication_name_id']]

        med_type_med_name_data[med['medication_name_id']
                               ][med['medication_type_id']] = True

    options = {}

    medication_dosages_data = MedicationMedicationNameMedicationDosageThrough.objects.values(
        'medication_name_id',
        'medication_dosage__id',
        'medication_dosage__name'
    ).order_by(
        'medication_dosage__order'
    )

    equivalent_medication_name_data = MedicationNameEquivalence.objects.values(
        'equivalent_medication_name_id',
        'medication_name_id'
    )

    for medication_name_id, medication_type_ids in med_type_med_name_data.items():
        medication_type_key = str(medication_type_ids.keys())

        medication_type_data = []
        for med_type_key in medication_type_ids.keys():
            medication_type_data.append({
                'id': med_type_key,
                'name': medication_type_mapping[med_type_key]
            })

        if medication_type_key not in options:
            options[medication_type_key] = {
                'medication_types': medication_type_data,
                'medication_names': [],
                'medication_dosages': []
            }

        equivalent_medication_name_ids = []

        for equivalent_medication_name_entry in equivalent_medication_name_data:
            if equivalent_medication_name_entry['medication_name_id'] == medication_name_id:
                equivalent_medication_name_ids.append(
                    equivalent_medication_name_entry['equivalent_medication_name_id'])

        med_obj = {
            'dosages': [],
            'id': medication_name_id,
            'name': str(medication_name_mapping[medication_name_id]),
            'equivalent_medication_name_ids': equivalent_medication_name_ids
        }

        medication_dosages = []

        for medication_dosages_entry in medication_dosages_data:
            if medication_dosages_entry['medication_name_id'] == medication_name_id:
                medication_dosages.append(medication_dosages_entry)

        for medication_dosage in medication_dosages:
            dosage_obj = {
                'id': medication_dosage['medication_dosage__id'],
                'name': medication_dosage['medication_dosage__name']
            }
            if dosage_obj not in med_obj['dosages']:
                med_obj['dosages'].append(dosage_obj)
                options[medication_type_key]['medication_dosages'].append(
                    dosage_obj)
        options[medication_type_key]['medication_names'].append(med_obj)

    return options.values()


class MedicationFiltersView(GenericAPIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        # 1 - Extract all request params
        date = self.request.query_params.get('map_date', False)
        dosages = self.request.query_params.getlist('dosages[]', [])
        drug_types = self.request.query_params.getlist('drug_types[]', [])
        med_id = self.request.query_params.get('med_id', None)
        provider_category_filters = self.request.query_params.getlist(
            'provider_categories[]', [])
        provider_type_filters = self.request.query_params.getlist(
            'provider_types[]', [])
        state_id = request.query_params.get('state_id', None)
        user = request.user
        zipcode = request.query_params.get('zipcode', None)

        # 2 - Check User permissions
        state_id, zipcode = force_user_state_id_and_zipcode(
            user, state_id, zipcode)

        # 3 - Extract all medications and medication ndcs codes filtered by Medication Name and Dosages
        provider_ids = get_provider_medication_id(
            request.query_params, field='provider_id')

        # 5 - Extract all active organization data with category and with a type
        organization_data = Provider.objects.filter(
            active=True,
            category__id__isnull=False,
            type__id__isnull=False
        ).values(
            'category__id',
            'category__name',
            'organization__id',
            'organization__organization_name',
            'type__id',
            'type__name'
        ).annotate(
            ignore_me=Count('organization__id'),
        )

        categories = {}
        types = {}

        # 6 - Build data structure for provider category filters and provider type filter
        for org_data in organization_data:
            category_id = org_data['category__id']
            organization_id = org_data['organization__id']
            type_id = org_data['type__id']

            category = categories[category_id] if category_id in categories else {
            }
            type = types[type_id] if type_id in types else {
            }

            type['id'] = type_id
            type['name'] = org_data['type__name']
            type['providers_count'] = 0
            types[type_id] = type

            category['id'] = category_id
            category['name'] = org_data['category__name']
            category['organizations'] = category['organizations'] if 'organizations' in category else {}

            category['organizations'][organization_id] = category['organizations'][
                organization_id] if organization_id in category['organizations'] else {}

            category['organizations'][organization_id]['disabled'] = True
            category['organizations'][organization_id]['organization_id'] = organization_id
            category['organizations'][organization_id]['organization_name'] = org_data['organization__organization_name']
            category['organizations'][organization_id]['providers_count'] = 0

            category['providers_count'] = 0
            categories[category_id] = category

        # 7 - Count Provider filtered by Category and Type
        provider_categories_and_types_count_qs = Provider.objects.filter(
            pk__in=provider_ids,
            active=True,
            category__id__isnull=False,
            type__id__isnull=False
        )

        if provider_category_filters:
            provider_categories_and_types_count_qs = provider_categories_and_types_count_qs.filter(
                category__id__in=provider_category_filters,
            )

        if provider_type_filters:
            provider_categories_and_types_count_qs = provider_categories_and_types_count_qs.filter(
                type__id__in=provider_type_filters,
            )

        # 8 - Add location filters if exists
        if state_id:
            provider_categories_and_types_count_qs = provider_categories_and_types_count_qs.filter(
                related_state_id=state_id
            )
        if zipcode:
            provider_categories_and_types_count_qs = provider_categories_and_types_count_qs.filter(
                related_zipcode__zipcode=zipcode
            )

        # we're dealing with a large data set, this query allows to capture
        # all proper counts in one query which takes around 160ms to execute
        provider_categories_and_types_count = provider_categories_and_types_count_qs.values(
            'category__id',
            'category__name',
            'organization__id',
            'organization__organization_name',
            'type__id',
            'type__name'
        ).annotate(
            providers_count=Count('id'),
        )

        # 9 - Add counts to types and categories data structures
        for count_data in provider_categories_and_types_count:
            category_id = count_data['category__id']
            organization_id = count_data['organization__id']
            type_id = count_data['type__id']
            types[type_id]['providers_count'] += count_data['providers_count']

            categories[category_id]['organizations'][organization_id]['disabled'] = False
            categories[category_id]['organizations'][organization_id]['providers_count'] += count_data['providers_count']
            categories[category_id]['providers_count'] += count_data['providers_count']

        # 10 - remove keys from data struct
        for category_id, category_values in categories.items():
            categories[category_id]['organizations'] = categories[category_id]['organizations'].values(
            )

        # 11 - build medication/drug type/dosages
        options = medication_name_dosage_type_filters()

        # 12 - load drug types
        drug_types = MedicationType.objects.order_by(
            'name').values('id', 'name')

        # 13 - remove more keys from data struct and build response
        filters = {
            'drug_types': drug_types,
            'formulations': options,
            'provider_categories': categories.values(),
            'provider_types': types.values(),
        }

        return Response(
            filters,
            status=status.HTTP_200_OK,
        )


class StateViewSet(viewsets.ModelViewSet):
    serializer_class = StateSerializer
    permission_classes = (IsAuthenticated,)
    allowed_methods = ['GET']

    def get_queryset(self):
        user = self.request.user
        states_qs = State.objects.all()

        state_id, zipcode = force_user_state_id_and_zipcode(user, None, None)

        if state_id:
            states_qs = states_qs.filter(id=state_id)

        ordering = self.request.query_params.get('ordering')
        if ordering and ('name' == ordering.replace('-', '')):
            if ordering.startswith('-'):
                states_qs = states_qs.order_by('-state_name')
            else:
                states_qs = states_qs.order_by('state_name')

        return states_qs


def get_provider_medication_id(query_params, field='id'):
    # Method use to save many line codes in the geo_stats views
    date = query_params.get('map_date', False)
    start_date = query_params.get('start_date', False)
    end_date = query_params.get('end_date', False)
    dosages = query_params.getlist('dosages[]', [])
    med_id = query_params.get('med_id', None)
    provider_category_filters = query_params.getlist(
        'provider_categories[]', [])
    provider_type_filters = query_params.getlist(
        'provider_types[]', [])

    # Find NDC code based on dosage and medication name
    med_ndc_ids = MedicationMedicationNameMedicationDosageThrough.objects.filter(
        medication_name_id=med_id,
        medication_dosage_id__in=dosages
    ).select_related(
        'medication__ndc_codes',
    ).distinct().values_list('medication__ndc_codes', flat=True)

    # First we take list of provider medication for this med, we will
    # use it for future filters

    # Annotate the list of the medication levels for every state
    # to be used to calculate the low/medium/high after in the serializer.
    # We create a list of the ids of the provider medication objects that
    # we have after filtering.

    provider_medication_qs = ProviderMedicationNdcThrough.objects.filter(
        medication_ndc_id__in=med_ndc_ids,
        provider__active=True,
        provider__category__in=provider_category_filters,
        provider__type__in=provider_type_filters,
    )

    if date:
        date = datetime.strptime(date, "%Y-%m-%d")
        provider_medication_qs = provider_medication_qs.filter(
            date=date,
        )
    elif start_date and end_date:
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
        provider_medication_qs = provider_medication_qs.filter(
            date__gte=start_date,
            date__lte=end_date + timedelta(days=1),
        )
    else:
        provider_medication_qs = provider_medication_qs.filter(
            latest=True,
        )

    provider_medication_ids = provider_medication_qs.values_list(
        field,
        flat=True,
    )

    return provider_medication_ids


class GeoStatsStatesWithMedicationsView(ListAPIView):
    serializer_class = GeoStateWithMedicationsSerializer
    permission_classes = (IsAuthenticated,)
    allowed_methods = ['GET']

    def get_queryset(self):
        '''
        query_params:
            - dosages: list of Dosage ids
            - drug_type: list of 1 character str, for drug_type in Medication
            - med_id: MedicationName id
            - provider_type: list of ProviderType ids
            - provider_category: list of ProviderCategory ids
        '''
        date = self.request.query_params.get('map_date', False)
        start_date = self.request.query_params.get('start_date', False)
        end_date = self.request.query_params.get('end_date', False)
        dosages = self.request.query_params.getlist('dosages[]', [])
        med_id = self.request.query_params.get('med_id', None)
        provider_category_filters = self.request.query_params.getlist(
            'provider_categories[]', [])
        provider_type_filters = self.request.query_params.getlist(
            'provider_types[]', [])

        # Find NDC code based on dosage and medication name
        med_ndc_ids = MedicationMedicationNameMedicationDosageThrough.objects.filter(
            medication_name_id=med_id,
            medication_dosage_id__in=dosages
        ).select_related(
            'medication__ndc_codes',
        ).distinct().values_list('medication__ndc_codes', flat=True)

        qs = State.objects.all().annotate(
            active_provider_count=Count(
                'providers__id',
                filter=Q(
                    providers__active=True,
                    providers__category__in=provider_category_filters,
                    providers__provider_medication__date=date,
                    providers__provider_medication__medication_ndc_id__in=med_ndc_ids,
                    providers__type__in=provider_type_filters,
                ),
                distinct=True
            ),
            total_provider_count=Count(
                'providers__id',
                distinct=True
            ),
            medication_levels=ArrayAgg(
                'providers__provider_medication__level',
                filter=Q(
                    providers__active=True,
                    providers__category__in=provider_category_filters,
                    providers__provider_medication__date=date,
                    providers__provider_medication__medication_ndc_id__in=med_ndc_ids,
                    providers__type__in=provider_type_filters,)
            ),
        )
        return qs


class GeoStatsCountiesWithMedicationsView(ListAPIView):
    serializer_class = GeoCountyWithMedicationsSerializer
    permission_classes = (SelfStatePermissionLevel,)
    allowed_methods = ['GET']

    def get_queryset(self):
        '''
        kwarg: state_id

        query_params:
            - med_id: MedicationName id
            - formulations: list of Medication ids
            - provider_type: list of ProviderType ids
            - provider_category: list of ProviderCategory ids
            - drug_type: list of 1 character str, for drug_type in Medication
        '''
        med_id = self.request.query_params.get('med_id')
        provider_category_filters = self.request.query_params.getlist(
            'provider_categories[]', [])
        provider_type_filters = self.request.query_params.getlist(
            'provider_types[]', [])
        state_id = self.kwargs.pop('state_id')
        user = self.request.user

        date = self.request.query_params.get('map_date', False)
        start_date = self.request.query_params.get('start_date', False)
        end_date = self.request.query_params.get('end_date', False)
        dosages = self.request.query_params.getlist('dosages[]', [])
        med_id = self.request.query_params.get('med_id', None)
        provider_category_filters = self.request.query_params.getlist(
            'provider_categories[]', [])
        provider_type_filters = self.request.query_params.getlist(
            'provider_types[]', [])

        state_id, zipcode = force_user_state_id_and_zipcode(
            user, state_id, None)

        try:
            if not med_id or int(
                med_id
            ) not in MedicationName.objects.values_list(
                'id',
                flat=True,
            ):
                return County.objects.filter(
                    state__id=state_id,
                ).select_related(
                    'state',
                ).annotate(
                    centroid=AsGeoJSON(Centroid('state__geometry')),
                )
        except ValueError:
            return County.objects.filter(
                state__id=state_id,
            ).select_related(
                'state',
            ).annotate(
                centroid=AsGeoJSON(Centroid('state__geometry')),
            )

        # Find NDC code based on dosage and medication name
        med_ndc_ids = MedicationMedicationNameMedicationDosageThrough.objects.filter(
            medication_name_id=med_id,
            medication_dosage_id__in=dosages
        ).select_related(
            'medication__ndc_codes',
        ).distinct().values_list('medication__ndc_codes', flat=True)

        qs = County.objects.filter(
            state_id=state_id,
        ).select_related(
            'state',
        ).annotate(
            active_provider_count=Count(
                'providers__id',
                filter=Q(
                    providers__active=True,
                    providers__category__in=provider_category_filters,
                    providers__provider_medication__date=date,
                    providers__provider_medication__medication_ndc_id__in=med_ndc_ids,
                    providers__type__in=provider_type_filters,
                ),
                distinct=True
            ),
            total_provider_count=Count(
                'providers__id',
                distinct=True
            ),
            medication_levels=ArrayAgg(
                'providers__provider_medication__level',
                filter=Q(
                    providers__active=True,
                    providers__category__in=provider_category_filters,
                    providers__provider_medication__date=date,
                    providers__provider_medication__medication_ndc_id__in=med_ndc_ids,
                    providers__type__in=provider_type_filters,
                )
            )
        )
        return qs


class GeoZipCodeWithMedicationsView(RetrieveAPIView):
    serializer_class = GeoZipCodeWithMedicationsSerializer
    permission_classes = (SelfZipCodePermissionLevel,)
    lookup_field = 'zipcode'

    def get_queryset(self):
        '''
        kwarg: zipcode

        query_params:
            - med_id: MedicationName id
            - formulations: list of Medication ids
            - provider_type: list of ProviderType ids
            - provider_category: list of ProviderCategory ids
            - drug_type: list of 1 character str, for drug_type in Medication
            - state_id: int of a state obj, used when more than one zipcode
        '''
        med_id = self.request.query_params.get('med_id')
        state_id = self.request.query_params.get('state_id')
        provider_category_filters = self.request.query_params.getlist(
            'provider_categories[]', [])
        provider_type_filters = self.request.query_params.getlist(
            'provider_types[]', [])

        user = self.request.user
        zipcode = self.kwargs.get('zipcode')

        # check permission
        state_id, zipcode = force_user_state_id_and_zipcode(
            user, state_id, zipcode)

        try:
            int(med_id)
        except (ValueError, TypeError):
            return ZipCode.objects.filter(zipcode=zipcode).annotate(
                centroid=AsGeoJSON(Centroid('geometry')),
            )
        provider_medication_ids = get_provider_medication_id(
            self.request.query_params,
        )
        if state_id:
            zipcode_qs = ZipCode.objects.filter(
                zipcode=zipcode,
                state=state_id,
            ).annotate(
                medication_levels=ArrayAgg(
                    'providers__provider_medication__level',
                    filter=Q(
                            providers__provider_medication__id__in=provider_medication_ids  # noqa
                    )
                ),
                centroid=AsGeoJSON(Centroid('geometry')),
            )
        else:
            zipcode_qs = ZipCode.objects.filter(zipcode=zipcode).annotate(
                active_provider_count=Count(
                    'providers__id',
                    filter=Q(
                        providers__active=True,
                        providers__category__id__isnull=False,
                        providers__type__id__isnull=False,
                        providers__provider_medication__id__in=provider_medication_ids
                    ),
                    distinct=True
                ),
                total_provider_count=Count(
                    'providers__id',
                    distinct=True
                ),
                medication_levels=ArrayAgg(
                    'providers__provider_medication__level',
                    filter=Q(
                        providers__provider_medication__id__in=provider_medication_ids  # noqa
                    )
                ),
                centroid=AsGeoJSON(Centroid('geometry')),
            )

        return zipcode_qs

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
        except MultipleObjectsReturned:
            zipcodes = self.get_queryset()
            states = [zipcode.state for zipcode in zipcodes]
            serializer = SimpleStateSerializer(states, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class OrganizationViewSet(viewsets.ModelViewSet):
    serializer_class = OrganizationSerializer
    permission_classes = (AllowAny,)
    allowed_methods = ['GET']
    queryset = Organization.objects.all()


class CSVExportView(GenericAPIView):
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
        user = request.user
        state_id = getattr(self, 'state_id', None)
        zipcode = getattr(self, 'zipcode', None)
        dosages = request.query_params.getlist('dosages[]', [])
        drug_types = request.query_params.getlist('drug_types[]', [])
        end_date = request.query_params.get('end_date')
        med_id = request.query_params.get('med_id')
        provider_categories = request.query_params.getlist(
            'provider_categories[]', [])
        provider_types = request.query_params.getlist(
            'provider_types[]', [])
        start_date = request.query_params.get('start_date')

        # check permission
        state_id, zipcode = force_user_state_id_and_zipcode(
            user, state_id, zipcode)

        # ensure correct geography filters
        if zipcode:
            geography = zipcode
        elif state_id:
            try:
                geography = State.objects.get(id=state_id).state_name
            except State.DoesNotExist:
                raise BadRequest('No such state exists')
        else:
            geography = 'US'

        try:
            med_name = MedicationName.objects.get(id=med_id)
        except MedicationName.DoesNotExist:
            raise BadRequest('No such medication in database')

        # collect NDC ids for dosages and med
        med_ndc_ids = MedicationMedicationNameMedicationDosageThrough.objects.filter(
            medication_name_id=med_id,
            medication_dosage_id__in=dosages
        ).select_related(
            'medication__ndc_codes',
        ).distinct().values_list('medication__ndc_codes', flat=True)

        filename = '{medication_name}_{geography}_{date_from}_{date_to}_{user_id}_{timestamp}.csv'.format(
            medication_name=med_name.name.replace(
                ' ', '_').replace('(', '').replace(')', ''),
            geography=geography,
            date_from=start_date.format('%Y-%m-%d'),
            date_to=end_date.format('%Y-%m-%d'),
            user_id=user.id,
            timestamp=str(time.time()),
        )

        if hasattr(settings, 'AWS_S3_BUCKET_NAME'):
            file_url = boto3.client('s3').generate_presigned_url(
                ClientMethod='get_object',
                Params={
                    'Bucket': settings.AWS_S3_BUCKET_NAME,
                    'Key': filename
                }
            )
        else:
            file_url = 'local_csv_url'

        generate_csv_export.delay(
            filename,
            file_url,
            user.id,
            med_id,
            start_date,
            end_date,
            list(med_ndc_ids),
            provider_types,
            provider_categories,
            drug_types,
            state_id,
            zipcode
        )

        return Response({
            'file_url': file_url
        })


class MedicationNameViewSet(viewsets.ModelViewSet):
    serializer_class = MedicationNameSerializer
    permission_classes = (AllowAny,)
    allowed_methods = ['GET']

    def get_queryset(self):
        medications_qs = MedicationName.objects.filter(pk__in=[1, 2])
        ordering = self.request.query_params.get('ordering')
        medications_related_qs = Medication.objects.all()
        drug_type_list = self.request.query_params.get(
            'drug_type',
            [],
        )
        provider_type_list = self.request.query_params.get(
            'provider_type',
            [],
        )

        provider_category_list = self.request.query_params.get(
            'provider_category',
            [],
        )
        if drug_type_list:
            medications_related_qs = medications_related_qs.filter(
                drug_type__in=drug_type_list,
            )
        if provider_type_list:
            medications_related_qs = medications_related_qs.filter(
                ndc_codes__provider_medication__provider__type__in=provider_type_list,  # noqa
            )
        if provider_category_list:
            medications_related_qs = medications_related_qs.filter(
                ndc_codes__provider_medication__provider__category__in=provider_category_list,  # noqa
            )

        medications_qs = medications_qs.prefetch_related(
            Prefetch(
                'medications',
                queryset=medications_related_qs.prefetch_related(
                    'ndc_codes',
                )
            )
        )

        if ordering and ('name' == ordering.replace('-', '')):
            if ordering.startswith('-'):
                medications_qs = medications_qs.order_by('-name')
            else:
                medications_qs = medications_qs.order_by('name')

        return medications_qs

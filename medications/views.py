import csv

from datetime import datetime, timedelta

from django.db.models import Q, Count
from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.gis.db.models.functions import Centroid, AsGeoJSON
from django.core.cache import cache
from django.db.models import IntegerField, Case, When, Sum, Value as V

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
from django.http import HttpResponse

from medications.tasks import generate_medications
from .serializers import (
    CSVUploadSerializer,
    MedicationNameSerializer,
    StateSerializer,
    GeoStateWithMedicationsSerializer,
    GeoCountyWithMedicationsSerializer,
    GeoZipCodeWithMedicationsSerializer,
    ProviderTypesAndCategoriesSerializer,
    OrganizationSerializer,
)
from .models import (
    County,
    MedicationName,
    Organization,
    ProviderMedicationThrough,
    ProviderType,
    ProviderCategory,
    State,
    ZipCode,
    Medication,
)

from .permissions import (
    NationalLevel,
    SelfStatePermissionLevel,
    SelfZipCodePermissionLevel,
)


class CSVUploadView(GenericAPIView):
    serializer_class = CSVUploadSerializer
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        csv_file = serializer.validated_data.pop('csv_file')
        organization_id = serializer.validated_data.pop('organization_id')
        cache_key = '{}_{}'.format('csv_uploaded_file', request.user.id)
        cache.set(cache_key, csv_file, None)
        generate_medications.delay(
            cache_key,
            organization_id,
        )
        return Response(
            {'status': _('The medications creation proccess has been queued')},
            status=status.HTTP_200_OK,
        )


class MedicationNameViewSet(viewsets.ModelViewSet):
    serializer_class = MedicationNameSerializer
    permission_classes = (AllowAny,)
    allowed_methods = ['GET']

    def get_queryset(self):
        medications_qs = MedicationName.objects.all()
        ordering = self.request.query_params.get('ordering')
        if ordering and ('name' == ordering.replace('-', '')):
            if ordering.startswith('-'):
                medications_qs = medications_qs.order_by('-name')
            else:
                medications_qs = medications_qs.order_by('name')

        return medications_qs.prefetch_related('medications')


class StateViewSet(viewsets.ModelViewSet):
    serializer_class = StateSerializer
    permission_classes = (IsAuthenticated,)
    allowed_methods = ['GET']

    def get_queryset(self):
        user_state = getattr(self.request.user, 'state', None)
        if user_state and \
           self.request.user.permission_level == self.request.user.STATE_LEVEL:
            states_qs = State.objects.filter(id=user_state.id)
        elif not user_state and \
            self.request.user.permission_level == \
                self.request.user.STATE_LEVEL:
            msg = _(
                'This user has not national level permission '
                'and no attached state'
            )
            raise BadRequest(msg)
        else:
            states_qs = State.objects.all()
        ordering = self.request.query_params.get('ordering')
        if ordering and ('name' == ordering.replace('-', '')):
            if ordering.startswith('-'):
                states_qs = states_qs.order_by('-state_name')
            else:
                states_qs = states_qs.order_by('state_name')
        return states_qs.annotate(
            county_list=ArrayAgg('counties__county_name'),
        )


def get_provider_medicatiopn_id(query_params):
    # Method use to save many line codes in the geo_stats views

    med_id = query_params.get('med_id')

    # First we take list of provider medication for this med, we will
    # use it for future filters
    provider_medication_qs = ProviderMedicationThrough.objects.filter(
        latest=True,
        medication__medication_name__id=med_id,
    )
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
            medication__id__in=formulation_ids,
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

    # Now we check if there is a list of drug types to filter
    drug_type_list = query_params.get(
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

    # Annotate the list of the medication levels for every state
    # to be used to calculate the low/medium/high after in the serializer.
    # We create a list of the ids of the provider medication objects that
    # we have after filtering.
    provider_medication_ids = provider_medication_qs.values_list(
        'id',
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
            - med_id: MedicationName id
            - formulations: list of Medication ids
            - provider_type: list of ProviderType ids
            - provider_category: list of ProviderCategory ids
            - drug_type: list of 1 character str, for drug_type in Medication
        '''
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
        provider_medication_ids = get_provider_medicatiopn_id(
            self.request.query_params,
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
        state_id = self.kwargs.pop('state_id')
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

        provider_medication_ids = get_provider_medicatiopn_id(
            self.request.query_params,
        )
        qs = County.objects.filter(
            state__id=state_id,
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
        '''
        med_id = self.request.query_params.get('med_id')
        zipcode = self.kwargs.get('zipcode')
        try:
            int(med_id)
        except (ValueError, TypeError):
            return ZipCode.objects.filter(zipcode=zipcode).annotate(
                centroid=AsGeoJSON(Centroid('geometry')),
            )
        provider_medication_ids = get_provider_medicatiopn_id(
            self.request.query_params,
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
        # TODO: Caught the exception and return a serializer with states to select
        if len(zipcode_qs) > 1:
            zipcode_qs = zipcode_qs.filter(
                population=max(zipcode_qs.values_list('population', flat=True))
            )
        return zipcode_qs

    # def get_object(self):
    #     try:
    #         super
    #     except Multiple


class ProviderTypesView(ListAPIView):
    serializer_class = ProviderTypesAndCategoriesSerializer
    permission_classes = (NationalLevel,)
    allowed_methods = ['GET']

    class Meta:
        model = ProviderType

    def get_queryset(self):
        '''
        query_params:
            - med_id: MedicationName id
            - formulations: list of Medication ids
            - state_id: id of State object
            - zipcode: zipcode
            - drug_type: list of 1 character str, for drug_type in Medication
        '''
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
        qs = self.Meta.model.objects.all().annotate(
            providers_count=Sum(
                Case(
                    When(
                        providers__provider_medication__id__in=provider_medication_ids, # noqa
                        then=V(1),
                    ),
                    output_field=IntegerField(),
                    default=V(0)
                ),
            ),
        )
        return qs


class ProviderCategoriesView(ProviderTypesView):
    # Inheritance from Provider types view since only the model
    class Meta:
        model = ProviderCategory


class OrganizationViewSet(viewsets.ModelViewSet):
    serializer_class = OrganizationSerializer
    permission_classes = (AllowAny,)
    allowed_methods = ['GET']
    queryset = Organization.objects.all()


class MedicationTypesView(views.APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        '''
        query_params:
            - med_id: MedicationName id
            - formulations: list of Medication ids
            - state_id: id of State object
            - zipcode: zipcode
            - provider_category: list of ProviderCategory ids
            - provider_type: list of ProviderType ids
        '''
        med_id = self.request.query_params.get('med_id')
        state_id = self.request.query_params.get('state_id')
        zipcode = self.request.query_params.get('zipcode')
        values = [
            {'drug_type': 'b', 'count': 0},
            {'drug_type': 'p', 'count': 0},
            {'drug_type': 'g', 'count': 0},
        ]
        for drug_type in values:
            drug_type['drug_type_verbose'] = dict(
                Medication.DRUG_TYPE_CHOICES
            ).get(drug_type['drug_type'])
        try:
            if not med_id or int(
                med_id
            ) not in MedicationName.objects.values_list(
                'id',
                flat=True,
            ):
                return Response(values)
        except ValueError:
            return Response(values)

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

        provider_medication_ids = provider_medication_qs.values_list(
            'id',
            flat=True,
        )
        values = Medication.objects.filter(
            provider_medication__id__in=provider_medication_ids,
        ).values('drug_type').annotate(count=Count('drug_type'))
        for drug_type in values:
            drug_type['drug_type_verbose'] = dict(
                Medication.DRUG_TYPE_CHOICES
            ).get(drug_type['drug_type'])
        return Response(values)


class CSVExportView(GenericAPIView):
    permission_classes = (AllowAny,)
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

    def get_queryset(self, state_id=None, zipcode=None):
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
        if zipcode:
            provider_medication_qs = ProviderMedicationThrough.objects.filter(
                medication__medication_name__id=med_id,
                provider__related_zipcode__zipcode=zipcode,
            )
        elif not zipcode and state_id:
            provider_medication_qs = ProviderMedicationThrough.objects.filter(
                medication__medication_name__id=med_id,
                provider__related_zipcode__state=state_id,
            )
        else:
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
        qs = ProviderMedicationThrough.objects.filter(
            creation_date__gte=start_date,
            creation_date__lte=end_date + timedelta(days=1),
        ).prefetch_related(
            'provider',
            'provider__organization',
            'provider__type',
            'provider__category',
            'medication',
            'medication__medication_name',
        )
        return qs

    def get(self, request):
        state_id = getattr(self, 'state_id', None)
        zipcode = getattr(self, 'zipcode', None)
        med_id = request.query_params.get('med_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if med_id and start_date and end_date:
            qs = self.get_queryset(
                state_id,
                zipcode,
            )

            # Generate the name for the file
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

            filename = '{medication_name}-{geography}_{date_from}-{date_to}.csv'.format( # noqa
                medication_name=med_name.name,
                geography=geography,
                date_from=start_date,
                date_to=end_date,
            )
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename={}'.format(
                filename,
            )
            header = [
                'Date',
                'Organization',
                'Provider ID',
                'Provider Name',
                'Provider Address',
                'Provider City',
                'Provider State',
                'Provider Zip',
                'Provider Type',
                'Pharmacy Category',
                'Medication Name',
                'Med ID',
                'Product Type',
                'Inventory',
                'Last Updated',
                'Latest',
            ]
            writer = csv.DictWriter(response, fieldnames=header)
            writer.writeheader()
            for instance in qs:
                data_row = (
                    instance.creation_date.date().isoformat(),
                    instance.provider.organization,
                    instance.provider.store_number,
                    instance.provider.name,
                    instance.provider.address,
                    instance.provider.city,
                    instance.provider.state,
                    instance.provider.zip,
                    instance.provider.type,
                    instance.provider.category,
                    instance.medication.medication_name,
                    instance.medication,
                    dict(Medication.DRUG_TYPE_CHOICES).get(
                        instance.medication.drug_type
                    ),
                    instance.supply,
                    instance.last_modified.ctime(),
                    instance.latest,
                )
                writer.writerow(dict(zip(header, data_row)))
            return response
        raise BadRequest('No med_id start_date or end_date in request')

import csv
import json

from collections import OrderedDict

from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from datetime import datetime
from rest_framework import serializers

from .constants import field_rows
from .models import (
    Medication,
    MedicationName,
    State,
    County,
    ZipCode,
    Organization,
    ProviderType,
)
from .utils import get_supplies


class CSVUploadSerializer(serializers.Serializer):
    csv_file = serializers.FileField()
    import_date = serializers.CharField(required=False)

    class Meta:
        fields = (
            'csv_file',
            'import_date',
        )

    def validate(self, data):
        user = self.context.get('request').user
        if hasattr(user, 'organization'):
            organization = user.organization
        else:
            organization = None
        if not organization:
            raise serializers.ValidationError(
                {'csv_file': _('No linked organization found for user')}
            )

        import_date = data.get('import_date', False)
        if import_date:
            try:
                import_date = datetime.strptime(
                    import_date, '%Y%m%d %H:%M:%S %z')
            except ValueError:
                raise serializers.ValidationError(
                    {'import_date': _('Invalid Import date format')}
                )

        file = data.get('csv_file')
        if not file.name.endswith('.csv'):
            raise serializers.ValidationError(
                {'csv_file': _('Unknown CSV format')}
            )
        decoded_file = file.read().decode('utf-8').splitlines()
        reader = csv.DictReader(decoded_file)
        if set(reader.fieldnames) != set(field_rows):
            raise serializers.ValidationError(
                {
                    'csv_file':
                    _(
                        'CSV file header format error, headers must be: {}.'
                    ). format(', '.join(field_rows))}
            )

        data['csv_file'] = file
        data['organization_id'] = organization.id
        data['import_date'] = import_date
        return data


class StateSerializer(serializers.ModelSerializer):
    county_list = serializers.SerializerMethodField()

    class Meta:
        model = State
        fields = (
            'id',
            'state_name',
            'state_code',
            'population',
            'county_list',
            'active_provider_count',
            'total_provider_count',
        )

    def get_county_list(self, obj):
        return obj.county_list


class SimpleStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = (
            'id',
            'state_name',
            'state_code',
        )


class MedicationSerializer(serializers.ModelSerializer):
    ndc_codes = serializers.SerializerMethodField()

    class Meta:
        model = Medication
        fields = (
            'id',
            'name',
            'ndc_codes',
        )

    def get_ndc_codes(self, obj):
        return [ndc_code.ndc for ndc_code in obj.ndc_codes.all()]


class MedicationNameSerializer(serializers.ModelSerializer):
    medications = MedicationSerializer(many=True)

    class Meta:
        model = MedicationName
        fields = (
            'id',
            'name',
            'medications',
        )


class GeoStateWithMedicationsListSerializer(serializers.ListSerializer):

    @property
    def data(self):
        return super(serializers.ListSerializer, self).data

    def to_representation(self, data):
        """
        Add GeoJSON compatible formatting to a serialized queryset list
        """
        return OrderedDict((
            ("type", "FeatureCollection"),
            ("zoom", settings.ZOOM_US),
            ("center", settings.GEOJSON_GEOGRAPHIC_CONTINENTAL_CENTER_US),
            ("features", super().to_representation(data))
        ))


class GeoCountyWithMedicationsListSerializer(serializers.ListSerializer):

    @property
    def data(self):
        return super(serializers.ListSerializer, self).data

    def to_representation(self, data):
        """
        Add GeoJSON compatible formatting to a serialized queryset list
        """

        if data:
            state_data = data[0]
            center = json.loads(state_data.centroid) if data else ''
        else:
            center = ''

        if not hasattr(state_data, 'medication_levels'):
            state_obj = state_data.state
            state = {
                'name': state_obj.state_name,
                'id': state_obj.id,
                'code': state_obj.state_code,
                'population': state_obj.population,
                'active_provider_count': state_obj.active_provider_count,
                'total_provider_count': state_obj.total_provider_count,
            }
            return OrderedDict((
                ("type", "FeatureCollection"),
                ("zoom", settings.ZOOM_STATE),
                ("center", center),
                ("state", state),
                ("features", [])
            ))

        flatten_medications_levels = [
            item for entry in data for item in entry.medication_levels
        ]

        supplies, supply = get_supplies(flatten_medications_levels)
        state_obj = state_data.state
        state = {
            'name': state_obj.state_name,
            'id': state_obj.id,
            'code': state_obj.state_code,
            'supplies': supplies,
            'supply': supply,
            'population': state_obj.population,
            'active_provider_count': state_obj.active_provider_count,
            'total_provider_count': state_obj.total_provider_count,

        }
        return OrderedDict((
            ("type", "FeatureCollection"),
            ("zoom", settings.ZOOM_STATE),
            ("center", center),
            ("state", state),
            ("features", super().to_representation(data))
        ))


def get_properties(instance, geographic_type=None):
    """
    Get the feature metadata which will be used for the GeoJSON
    "properties" key.

    """
    properties = OrderedDict()
    if geographic_type == 'state':
        properties['name'] = instance.state_name
        properties['code'] = instance.state_code
        properties['id'] = instance.id
    elif geographic_type == 'county':
        properties['name'] = instance.county_name
    elif geographic_type == 'zipcode':
        properties['zipcode'] = instance.zipcode
        properties['state'] = {
            'name': instance.state.state_name,
            'id': instance.state.id,
            'population': instance.state.population
        }
    if hasattr(instance, 'medication_levels'):
        supplies, supply = get_supplies(instance.medication_levels)
    else:
        # We pass an empty list only to receive that are no supplies
        # in case when med_id is nor in the request. We need to pass
        # those keys to the frontend.
        supplies, supply = get_supplies([])
    properties['supplies'] = supplies
    properties['supply'] = supply
    properties['population'] = instance.population
    properties['total_provider_count'] = instance.total_provider_count
    properties['active_provider_count'] = instance.active_provider_count

    return properties


class GeoJSONWithMedicationsSerializer(serializers.ModelSerializer):

    @classmethod
    def many_init(cls, *args, **kwargs):
        child_serializer = cls(*args, **kwargs)
        list_kwargs = {'child': child_serializer}
        list_kwargs.update(dict([
            (key, value) for key, value in kwargs.items()
            if key in serializers.LIST_SERIALIZER_KWARGS
        ]))
        meta = getattr(cls, 'Meta', None)
        list_serializer_class = getattr(
            meta,
            'list_serializer_class',
        )
        return list_serializer_class(*args, **list_kwargs)

    def to_representation(self, instance):
        """
        Serialize objects -> primitives.
        """
        # prepare OrderedDict geojson structure
        feature = OrderedDict()

        # required type attribute
        # must be "Feature" according to GeoJSON spec
        feature["type"] = "Feature"

        # required geometry attribute
        # MUST be present in output according to GeoJSON spec
        feature["geometry"] = json.loads(
            instance.geometry.geojson
        ) if instance.geometry else None

        # GeoJSON properties
        geographic_type = getattr(
            self.Meta,
            'geographic_type',
        )
        feature["properties"] = get_properties(
            instance, geographic_type)

        return feature


class GeoStateWithMedicationsSerializer(GeoJSONWithMedicationsSerializer):

    class Meta:
        model = State
        fields = '__all__'
        list_serializer_class = GeoStateWithMedicationsListSerializer
        geographic_type = 'state'


class GeoCountyWithMedicationsSerializer(GeoJSONWithMedicationsSerializer):

    class Meta:
        model = County
        fields = '__all__'
        list_serializer_class = GeoCountyWithMedicationsListSerializer
        geographic_type = 'county'


class GeoZipCodeWithMedicationsSerializer(serializers.ModelSerializer):
    zoom = serializers.SerializerMethodField()
    center = serializers.SerializerMethodField()
    properties = serializers.SerializerMethodField()
    geometry = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()

    class Meta:
        model = ZipCode
        fields = (
            'type',
            'zoom',
            'center',
            'properties',
            'geometry',
        )

    def get_type(self, obj):
        return 'Feature'

    def get_zoom(self, data):
        return settings.ZOOM_ZIPCODE

    def get_center(self, obj):
        return json.loads(obj.centroid)

    def get_properties(self, obj):
        properties = get_properties(obj, 'zipcode')
        return properties

    def get_geometry(self, obj):
        return json.loads(obj.geometry.geojson)


class ProviderCategoriesSerializer(serializers.Serializer):

    def to_representation(self, organization_categories):
        categories = {}
        for organization_category in organization_categories:
            category_id = organization_category['category__id']
            category = categories[category_id] if category_id in categories else {
            }
            category['id'] = category_id
            category['name'] = organization_category['category__name']
            category['organizations'] = category['organizations'] if 'organizations' in category else []
            category['organizations'].append({
                'organization_id': organization_category['organization__id'],
                'organization_name': organization_category['organization__organization_name'],
                'providers_count': organization_category['providers_count']
            })
            category['providers_count'] = category['providers_count'] if 'providers_count' in category else 0
            category['providers_count'] += organization_category['providers_count']
            categories[category['id']] = category

        return categories.values()


class ProviderTypesSerializer(serializers.Serializer):

    def to_representation(self, organization_types):
        types = []
        for organization_type in organization_types:
            types.append({
                'id': organization_type['type__id'],
                'name': organization_type['type__name'],
                'providers_count': organization_type['providers_count'],
            })
        return types


class OrganizationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Organization
        fields = (
            'id',
            'organization_name',
            'contact_name',
            'phone',
            'website',
            'registration_date',
        )

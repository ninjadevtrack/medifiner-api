import csv
import datetime
import json

from collections import OrderedDict

from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from rest_framework import serializers
from rest_registration.exceptions import BadRequest

from historic.utils import daterange

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

    class Meta:
        fields = (
            'csv_file',
        )

    def validate(self, data):
        user = self.context.get('request').user
        if hasattr(user, 'organization'):
            organization = user.organization
        else:
            organization = None
        if not organization:
            raise serializers.ValidationError(
                {'csv_file': _('This user has not organization related.')}
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
                        'Wrong headers in CSV file, headers must be: {}.'
                    ). format(', '.join(field_rows))}
            )
        data['csv_file'] = file
        data['organization_id'] = organization.id

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
        )

    def get_county_list(self, obj):
        return obj.county_list


class MedicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medication
        fields = (
            'id',
            'name',
            'ndc',
        )


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
        if not hasattr(data[0], 'medication_levels'):
            state_obj = data[0].state
            state = {
                'name': state_obj.state_name,
                'id': state_obj.id,
                'code': state_obj.state_code,
                'population': state_obj.population,
            }
            return OrderedDict((
                ("type", "FeatureCollection"),
                ("zoom", settings.ZOOM_STATE),
                ("center", json.loads(data[0].centroid) if data else ''),
                ("state", state),
                ("features", [])
            ))
        medication_levels_list = data.values_list(
            'medication_levels',
            flat=True,
        )
        flatten_medications_levels = [
            item for sublist in medication_levels_list for item in sublist
        ]
        supplies, supply = get_supplies(flatten_medications_levels)
        state_obj = data[0].state
        state = {
            'name': state_obj.state_name,
            'id': state_obj.id,
            'code': state_obj.state_code,
            'supplies': supplies,
            'supply': supply,
            'population': state_obj.population,
        }
        return OrderedDict((
            ("type", "FeatureCollection"),
            ("zoom", settings.ZOOM_STATE),
            ("center", json.loads(data[0].centroid) if data else ''),
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
        properties['supplies'] = supplies
        properties['supply'] = supply
    properties['population'] = instance.population
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

        feature["geometry"] = \
            json.loads(
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


class ProviderTypesAndCategoriesSerializer(serializers.ModelSerializer):
    # We can use this serializer for categories as well even if model is
    # ProviderType since they have the same fields
    providers_count = serializers.SerializerMethodField()

    class Meta:
        model = ProviderType
        fields = ('id', 'code', 'name', 'providers_count')

    def get_providers_count(self, obj):
        return obj.providers_count


class ProviderCategoriesSerializer(serializers.ModelSerializer):
    providers_count = serializers.SerializerMethodField()

    class Meta:
        model = ProviderType
        fields = ('id', 'code', 'name', 'providers_count')

    def get_providers_count(self, obj):
        return obj.providers_count


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


class CSVExportSerializer(serializers.Serializer):

    class Meta:
        model = Medication
        fields = (
            'name',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        date_format = '%Y-%m-%d'
        start_date = self.context[
            'request'
        ].query_params.get('start_date')
        start_date = datetime.datetime.strptime(
            start_date,
            date_format,
        )

        end_date = self.context[
            'request'
        ].query_params.get('end_date')
        end_date = datetime.datetime.strptime(
            end_date,
            date_format,
        )
        for date in daterange(start_date, end_date, inclusive=True):
            self.Meta.fields += (date.date().isoformat(),)
            self.fields[date.date().isoformat()] = serializers.CharField()

    def to_representation(self, instance):
        data = OrderedDict()
        data['name'] = instance.name

        pm_qs = instance.provider_medication.all()
        date_format = '%Y-%m-%d'
        start_date = self.context[
            'request'
        ].query_params.get('start_date')
        start_date = datetime.datetime.strptime(
            start_date,
            date_format,
        )

        end_date = self.context[
            'request'
        ].query_params.get('end_date')
        end_date = datetime.datetime.strptime(
            end_date,
            date_format,
        )
        for date in daterange(start_date, end_date, inclusive=True):
            supply_levels = []
            if pm_qs:
                for pm in pm_qs:
                    if pm.date.day == date.day:
                        supply_levels.append(pm.level)
            data[date.date().isoformat()] = get_supplies(supply_levels)[1]
        return data

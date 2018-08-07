import csv
import json

from collections import OrderedDict

from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from rest_framework import serializers

from .constants import field_rows
from .models import (
    MedicationName,
    Medication,
    State,
    County,
    ZipCode,
    Provider,
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
        medication_levels_list = data.values_list(
            'medication_levels',
            flat=True,
        )
        flatten_medications_levels = [
            item for sublist in medication_levels_list for item in sublist
        ]
        supplies, supply = get_supplies(flatten_medications_levels)
        return OrderedDict((
            ("type", "FeatureCollection"),
            ("zoom", settings.ZOOM_STATE),
            ("center", json.loads(data[0].centroid) if data else ''),
            ("state_supplies", supplies),
            ("state_supply", supply),
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
    elif geographic_type == 'county':
        properties['name'] = instance.county_name
        properties['state'] = {
            'name': instance.state.state_name,
            'id': instance.state.id,
            'code': instance.state.state_code,
        }
    elif geographic_type == 'zipcode':
        properties['zipcode'] = instance.zipcode
        properties['state'] = {
            'name': instance.state.state_name,
            'id': instance.state.id,
        }
    supplies, supply = get_supplies(instance.medication_levels)
    properties['supplies'] = supplies
    properties['supply'] = supply
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
        # cls.geographic_type = getattr(meta, 'geographic_type', 'state')
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


class ProviderTypesSerializer(serializers.Serializer):
    def to_representation(self, data):
        provider_type = OrderedDict()
        provider_type['name'] = dict(
            Provider.TYPE_CHOICES
        ).get(data.get('type'))
        provider_type['code'] = data.get('type')
        provider_type['count'] = data.get('type__count')
        return provider_type



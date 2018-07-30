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
            ("zoom", 2),
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
        return OrderedDict((
            ("type", "FeatureCollection"),
            ("zoom", 10),
            ("center", json.loads(data[0].centroid)),
            ("features", super().to_representation(data))
        ))


def get_properties(instance, geographic_type):
    """
    Get the feature metadata which will be used for the GeoJSON
    "properties" key.

    """
    properties = OrderedDict()
    if geographic_type == 'state':
        properties['name'] = instance.state_name
    elif geographic_type == 'county':
        properties['name'] = instance.county_name
    # ZIPCODE?
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
        feature["geometry"] = json.loads(instance.geometry.geojson)

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

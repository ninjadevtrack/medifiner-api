import csv
from collections import OrderedDict

from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

from .constants import field_rows
from .models import ProviderMedicationThrough, MedicationName, Medication, State


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
    class Meta:
        model = State
        fields = (
            'id',
            'state_name',
            'state_code',
        )

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
            ("center", ""),# TODO
            ("features", super().to_representation(data))
        ))

class GeoStateWithMedicationsSerializer(serializers.ModelSerializer):

    class Meta:
        model = State
        fields = '__all__'

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
            GeoStateWithMedicationsListSerializer,
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
        feature["geometry"] = instance.geometry

        # GeoJSON properties
        feature["properties"] = self.get_properties(instance)

        return feature

    def get_properties(self, instance):
        """
        Get the feature metadata which will be used for the GeoJSON
        "properties" key.

        By default it returns all serializer fields excluding those used for
        the geometry and the bounding box.

        """
        properties = OrderedDict()
        properties['name'] = instance.state_name
        # TODO get_supply to make the calculation
        properties['supply'] = {'low': 0, 'medium': 0, 'high': 0}

        return properties

    def to_internal_value(self, data):
        """
        Override the parent method to first remove the GeoJSON formatting
        """
        if 'properties' in data:
            data = self.unformat_geojson(data)
        return super().to_internal_value(data)

    def unformat_geojson(self, feature):
        """
        This function should return a dictionary containing keys which maps
        to serializer fields.
        Remember that GeoJSON contains a key "properties" which contains the
        feature metadata. This should be flattened to make sure this
        metadata is stored in the right serializer fields.
        :param feature: The dictionary containing the feature data directly
                        from the GeoJSON data.
        :return: A new dictionary which maps the GeoJSON values to
                 serializer fields
        """
        attrs = feature["properties"]

        if 'geometry' in feature:
            attrs[self.Meta.geo_field] = feature['geometry']

        return attrs

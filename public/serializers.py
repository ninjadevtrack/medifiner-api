import json

from collections import OrderedDict
from rest_framework import serializers

from medications.models import ProviderMedicationThrough, Provider
from medications.utils import get_supplies


class ProviderMedicationSimpleSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='medication.id')
    medication_name = serializers.CharField(
        source='medication.medication_name',
    )
    name = serializers.CharField(source='medication.name')
    drug_type = serializers.SerializerMethodField()
    supply_level = serializers.SerializerMethodField()

    class Meta:
        model = ProviderMedicationThrough
        fields = (
            'id',
            'medication_name',
            'name',
            'drug_type',
            'supply_level',
        )

    def get_drug_type(self, obj):
        return obj.medication.get_drug_type_display()

    def get_supply_level(self, obj):
        levels, verbose = get_supplies([obj.level])
        return {'supplies': levels, 'supply': verbose}


class GeoJSONFindProviderListSerializer(serializers.ListSerializer):

    @property
    def data(self):
        return super(serializers.ListSerializer, self).data

    def to_representation(self, data):
        """
        Add GeoJSON compatible formatting to a serialized queryset list
        """
        return OrderedDict((
            ("type", "FeatureCollection"),
            ("features", super().to_representation(data))
        ))


class FindProviderSerializer(serializers.ModelSerializer):

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

    distance = serializers.SerializerMethodField()
    supply = serializers.SerializerMethodField()
    localization = serializers.SerializerMethodField()
    all_other_medications_provider = serializers.SerializerMethodField()

    class Meta:
        model = Provider
        list_serializer_class = GeoJSONFindProviderListSerializer
        exclude = ()

    def get_properties(self, instance):
        """
        Get the feature metadata which will be used for the GeoJSON
        "properties" key.

        """
        properties = OrderedDict()
        properties['id'] = instance.id
        properties['name'] = instance.name
        properties['address'] = instance.full_address
        properties['phone'] = instance.phone.as_national
        properties['website'] = instance.website
        properties['email'] = instance.email
        properties['operating_hours'] = instance.operating_hours
        properties['insurance_accepted'] = instance.insurance_accepted
        properties['distance'] = instance.distance.mi
        properties['store_number'] = instance.store_number
        properties['drugs'] = ProviderMedicationSimpleSerializer(
            instance.provider_medication.all(),
            many=True,
        ).data

        return properties

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
                instance.geo_localization.json
        ) if hasattr(instance, 'geo_localization') else None

        # GeoJSON properties

        feature["properties"] = self.get_properties(
            instance,
        )

        return feature


class ContactFormSerializer(serializers.Serializer):
    representative_name = serializers.CharField(max_length=255)
    pharmacy_name = serializers.CharField(max_length=255)
    pharmacy_address = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    additional_comments = serializers.CharField(allow_blank=True)

    class Meta:
        fields = (
            'representative_name',
            'email',
            'pharmacy_name',
            'pharmacy_address',
            'additional_comments',
        )

import json

from collections import OrderedDict
from rest_framework import serializers

from medications.models import ProviderMedicationThrough, Provider
from medications.utils import get_supplies


class ProviderMedicationSimpleSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='medication.name')
    supply = serializers.SerializerMethodField()

    class Meta:
        model = ProviderMedicationThrough
        fields = ('name', 'supply')

    def get_supply(self, obj):
        return get_supplies([obj.level])[1]


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

        if hasattr(instance, 'medication_levels'):
            supplies, supply = get_supplies(instance.medication_levels)
        else:
            supplies, supply = get_supplies([])
        properties['drug'] = {}
        properties['drug']['supply'] = supply
        properties['drug']['supplies'] = supplies
        properties['other_drugs'] = ProviderMedicationSimpleSerializer(
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

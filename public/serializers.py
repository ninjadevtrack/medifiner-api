import json

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


class FindProviderSerializer(serializers.ModelSerializer):
    distance = serializers.SerializerMethodField()
    supply = serializers.SerializerMethodField()
    localization = serializers.SerializerMethodField()
    all_other_medications_provider = serializers.SerializerMethodField()

    class Meta:
        model = Provider
        fields = (
            'id',
            'name',
            'full_address',
            'phone',
            'website',
            'email',
            'operating_hours',
            'insurance_accepted',
            'localization',
            'supply',
            'distance',
            'all_other_medications_provider',
        )

    def get_distance(self, obj):
        # return distance in miles
        return obj.distance.mi

    def get_supply(self, obj):
        # Take only the verbose supply for this serializer
        return get_supplies(obj.medication_levels)[1]

    def get_all_other_medications_provider(self, obj):
        return ProviderMedicationSimpleSerializer(
            obj.provider_medication.all(),
            many=True,
        ).data

    def get_localization(self, obj):
        if hasattr(obj, 'geo_localization'):
            return json.loads(obj.geo_localization.json)
        return None


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

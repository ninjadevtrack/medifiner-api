import datetime

from collections import OrderedDict

from rest_framework import serializers

from medications.models import Medication
from medications.utils import get_supplies

from .utils import daterange, get_overall


class AverageSupplyLevelListSerializer(serializers.ListSerializer):

    @property
    def data(self):
        return super(serializers.ListSerializer, self).data

    def to_representation(self, data):
        return OrderedDict((
            ('medication_supplies', super().to_representation(data)),
        ))


class AverageSupplyLevelZipCodeListSerializer(serializers.ListSerializer):

    @property
    def data(self):
        return super(serializers.ListSerializer, self).data

    def to_representation(self, data):
        try:
            return OrderedDict((
                (
                    'state',
                    data.first(
                    ).provider_medication.first(
                    ).provider.related_zipcode.state.id),
                ('medication_supplies', super().to_representation(data)),
            ))
        except AttributeError:
            return OrderedDict((
                ('state', None),
                ('medication_supplies', []),
            ))


class AverageSupplyLevelSerializer(serializers.ModelSerializer):
    average_supply_per_day = serializers.SerializerMethodField()

    class Meta:
        model = Medication
        list_serializer_class = AverageSupplyLevelListSerializer
        fields = (
            'name',
            'average_supply_per_day',
        )

    def get_average_supply_per_day(self, obj):
        pm_qs = obj.provider_medication.all()
        days = []
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
            days.append(
                {
                    'day': date.date(),
                    'supply': get_supplies(supply_levels),
                }
            )
        return days


class AverageSupplyLevelZipCodeSerializer(AverageSupplyLevelSerializer):

    class Meta:
        model = Medication
        list_serializer_class = AverageSupplyLevelZipCodeListSerializer
        fields = (
            'name',
            'average_supply_per_day',
        )


class OverallSupplyLevelSerializer(serializers.ModelSerializer):
    overall_supply_per_day = serializers.SerializerMethodField()

    class Meta:
        model = Medication
        fields = (
            'name',
            'overall_supply_per_day',
        )

    def get_overall_supply_per_day(self, obj):
        pm_qs = obj.provider_medication.all()
        days = []
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
            days.append(
                {
                    'day': date.date(),
                    'supply': get_overall(supply_levels),
                }
            )
        return days

import datetime

from rest_framework import serializers

from medications.models import Medication
from medications.utils import get_supplies

from .utils import daterange


class AverageSupplyLevelSerializer(serializers.ModelSerializer):
    average_supply_per_day = serializers.SerializerMethodField()

    class Meta:
        model = Medication
        fields = (
            'name',
            'average_supply_per_day',
        )

    def get_average_supply_per_day(self, obj):
        pm_qs = obj.provider_medication.all()
        days = []
        date_format = '%Y-%m-%dT%H:%M:%S.%fZ'

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
                    'day': date.isoformat(),
                    'supply': get_supplies(supply_levels),
                }
            )
        return days

import datetime

from collections import OrderedDict

from rest_framework import serializers

from medications.models import Medication, ZipCode, MedicationName
from medications.utils import get_supplies

from .utils import daterange, get_overall


class AverageSupplyLevelSerializer(serializers.Serializer):


    def to_representation(self, data):
        medication_data = []
        medication_ids = data.values_list('medication_ndc_id', flat=True)

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

        for medication_id in medication_ids:
            days = []
            filtered_qs = data.filter(medication_ndc_id=medication_id)
            medication_name = data.first().get('medication_ndc__medication__name')
            for date in daterange(start_date, end_date, inclusive=True):
                supply_levels = []
                for provider_medication in filtered_qs:
                    if provider_medication.get(
                        'creation_date',
                    ).day == date.day:
                        supply_levels.append(provider_medication.get('level'))
                days.append(
                    {
                        'day': date.date(),
                        'supply': get_supplies(supply_levels),
                    }
                )
            medication_data.append({
                'name': medication_name, 'average_supply_per_day': days
            })

        return OrderedDict((
            ('medication_supplies', medication_data),
        ))


class AverageSupplyLevelZipCodeListSerializer(serializers.ListSerializer):

    # @property
    # def data(self):
        # return super(serializers.ListSerializer, self).data

    def to_representation(self, data):
        zipcode = self.context['request'].data.get('zipcode')
        if zipcode:
            zipcode_obj = ZipCode.objects.filter(zipcode=zipcode)
        if zipcode_obj:
            return OrderedDict((
                ('state', zipcode_obj[0].state.id),
                ('medication_supplies', super().to_representation(data)),
            ))
        else:
            return OrderedDict((
                ('state', None),
                ('medication_supplies', super().to_representation(data)),
            ))


# class AverageSupplyLevelSerializer(serializers.ModelSerializer):
#     # average_supply_per_day = serializers.SerializerMethodField()

#     class Meta:
#         list_serializer_class = AverageSupplyLevelListSerializer
#         fields = (
#             'name',
            # 'average_supply_per_day',
        # )

    # def get_average_supply_per_day(self, obj):
    #     provider_medication_qs = []
    #     for ndc_code in obj.ndc_codes.all():
    #         for provider_medication in ndc_code.provider_medication.all():
    #             provider_medication_qs.append(provider_medication)
    #     days = []
    #     date_format = '%Y-%m-%d'
    #     start_date = self.context[
    #         'request'
    #     ].query_params.get('start_date')
    #     start_date = datetime.datetime.strptime(
    #         start_date,
    #         date_format,
    #     )

    #     end_date = self.context[
    #         'request'
    #     ].query_params.get('end_date')
    #     end_date = datetime.datetime.strptime(
    #         end_date,
    #         date_format,
    #     )
    #     for date in daterange(start_date, end_date, inclusive=True):
    #         supply_levels = []
    #         if provider_medication_qs:
    #             for provider_medication in provider_medication_qs:
    #                 if provider_medication.creation_date.day == date.day:
    #                     supply_levels.append(provider_medication.level)
    #         days.append(
    #             {
    #                 'day': date.date(),
    #                 'supply': get_supplies(supply_levels),
    #             }
    #         )
        # return days


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
        model = MedicationName
        # list_serializer_class = AverageSupplyLevelListSerializer
        fields = (
            'overall_supply_per_day',
        )

    def get_overall_supply_per_day(self, obj):
        medications_qs = obj.medications.all()
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
            if medications_qs:
                for medication in medications_qs:
                    for ndc_code in medication.ndc_codes.all():
                        for provider_medication in \
                                ndc_code.provider_medication.all():
                            if provider_medication.creation_date.day == \
                               date.day:
                                supply_levels.append(provider_medication.level)
            days.append(
                {
                    'day': date.date(),
                    'supply': get_overall(supply_levels),
                }
            )
        return days


class OverallSupplyLevelZipCodeSerializer(OverallSupplyLevelSerializer):

    class Meta:
        model = MedicationName
        list_serializer_class = AverageSupplyLevelZipCodeListSerializer
        fields = (
            'overall_supply_per_day',
        )

import datetime

from collections import OrderedDict

from rest_framework import serializers

from medications.models import Medication, ZipCode, MedicationName
from medications.utils import get_supplies, get_dominant_supply

from .utils import daterange, get_overall, percentage


class AverageSupplyLevelSerializer(serializers.Serializer):

    def to_representation(self, medication_ndcs, provider_medication_ndcs):
        aggregated_data = {}

        ndc_map = {}

        for ndc in medication_ndcs:
            ndc_map[ndc['id']] = ndc['medication__name']

        for provider_medication_ndc in provider_medication_ndcs:
            creation_date = provider_medication_ndc["creation_date_only"].strftime(
                '%Y-%m-%d')
            count_for_level = provider_medication_ndc["count_for_level"]
            level = provider_medication_ndc["level"]
            medication_ndc_id = provider_medication_ndc["medication_ndc_id"]
            medication_name = ndc_map[medication_ndc_id]

            if not medication_name in aggregated_data:
                aggregated_data[medication_name] = {}

            if not creation_date in aggregated_data[medication_name]:
                aggregated_data[medication_name][creation_date] = {}

            if not level in aggregated_data[medication_name][creation_date]:
                aggregated_data[medication_name][creation_date][level] = 0

            aggregated_data[medication_name][creation_date][level] += count_for_level

        api_data = []
        for med_name, med_data in aggregated_data.items():
            formatted_data = {}
            formatted_data["name"] = med_name
            formatted_data["average_supply_per_day"] = []
            for date, supply_levels in med_data.items():
                no_supply = supply_levels[0] if 0 in supply_levels else 0
                low = supply_levels[1] if 1 in supply_levels else 0
                medium = supply_levels[3] if 3 in supply_levels else 0
                high = supply_levels[4] if 4 in supply_levels else 0

                formatted_data["average_supply_per_day"].append({
                    "day": date,
                    "supply": [{
                        "no_supply": no_supply,
                        "low": low,
                        "medium": medium,
                        "high": high
                    }, get_dominant_supply(low, medium, high, low + medium + high)]
                })
            api_data.append(formatted_data)

        return api_data


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


class OverallSupplyLevelSerializer(serializers.Serializer):

    def to_representation(self, provider_medication_ndcs):
        aggregated_data = {}

        for provider_medication_ndc in provider_medication_ndcs:
            creation_date = provider_medication_ndc["creation_date_only"].strftime(
                '%Y-%m-%d')
            count_for_level = provider_medication_ndc["count_for_level"]
            level = provider_medication_ndc["level"]

            if not creation_date in aggregated_data:
                aggregated_data[creation_date] = {}

            aggregated_data[creation_date][level] = count_for_level

        api_data = []
        for date, date_data in aggregated_data.items():
            formatted_data = {}
            formatted_data["day"] = date
            low = date_data[1]
            medium = date_data[3]
            high = date_data[4]
            total = low + medium + high
            formatted_data["supply"] = {
                "low": percentage(low, total),
                "medium": percentage(medium, total),
                "high": percentage(high, total),
            }
            api_data.append(formatted_data)

        return api_data


class OverallSupplyLevelZipCodeSerializer(OverallSupplyLevelSerializer):

    class Meta:
        model = MedicationName
        list_serializer_class = AverageSupplyLevelZipCodeListSerializer
        fields = (
            'overall_supply_per_day',
        )

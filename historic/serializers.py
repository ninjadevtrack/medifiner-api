import datetime

from rest_framework import serializers

from medications.utils import get_dominant_supply

from .utils import daterange, percentage


class AverageSupplyLevelSerializer(serializers.Serializer):

    def to_representation(self, medication_ndcs, provider_medication_ndcs):
        aggregated_data = {}
        ndc_map = {}

        for ndc in medication_ndcs:
            ndc_map[ndc['id']] = ndc['medication__name']

        for provider_medication_ndc in provider_medication_ndcs:
            creation_date = provider_medication_ndc[
                'creation_date_only'
            ].strftime(
                '%Y-%m-%d')
            count_for_level = provider_medication_ndc['count_for_level']
            level = provider_medication_ndc['level']
            medication_ndc_id = provider_medication_ndc['medication_ndc_id']
            medication_name = ndc_map[medication_ndc_id]

            if medication_name not in aggregated_data:
                aggregated_data[medication_name] = {}

            if creation_date not in aggregated_data[medication_name]:
                aggregated_data[medication_name][creation_date] = {}

            if level not in aggregated_data[medication_name][creation_date]:
                aggregated_data[medication_name][creation_date][level] = 0

            aggregated_data[
                medication_name
            ][creation_date][level] += count_for_level

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

        api_data = []
        for med_name, med_data in aggregated_data.items():
            formatted_data = {}
            formatted_data['name'] = med_name
            formatted_data['average_supply_per_day'] = []
            for date in daterange(start_date, end_date, inclusive=True):
                formatted_date = date.strftime(
                    '%Y-%m-%d')
                supply_levels = med_data[
                    formatted_date
                ] if formatted_date in med_data else {}
                no_supply = supply_levels[0] if 0 in supply_levels else 0
                low = supply_levels[1] if 1 in supply_levels else 0
                medium = supply_levels[3] if 3 in supply_levels else 0
                high = supply_levels[4] if 4 in supply_levels else 0
                formatted_data["average_supply_per_day"].append({
                    "day": date.date(),
                    "supply": [{
                        "no_supply": no_supply,
                        "low": low,
                        "medium": medium,
                        "high": high
                    }, get_dominant_supply(
                        low,
                        medium,
                        high,
                        low + medium + high,
                    )
                    ]
                })
            api_data.append(formatted_data)

        return api_data


class OverallSupplyLevelSerializer(serializers.Serializer):

    def to_representation(self, provider_medication_ndcs):
        aggregated_data = {}

        for provider_medication_ndc in provider_medication_ndcs:
            creation_date = provider_medication_ndc[
                'creation_date_only'
            ].strftime(
                '%Y-%m-%d')
            count_for_level = provider_medication_ndc['count_for_level']
            level = provider_medication_ndc['level']

            if creation_date not in aggregated_data:
                aggregated_data[creation_date] = {}
            aggregated_data[creation_date][level] = count_for_level

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

        api_data = []

        for date in daterange(start_date, end_date, inclusive=True):
            formatted_data = {}
            formatted_date = date.strftime(
                '%Y-%m-%d')
            formatted_data["day"] = formatted_date

            date_data = aggregated_data[
                formatted_date
            ] if formatted_date in aggregated_data else {}

            low = date_data[1] if 1 in date_data else 0
            medium = date_data[3] if 3 in date_data else 0
            high = date_data[4] if 4 in date_data else 0
            total = low + medium + high
            formatted_data["supply"] = {
                "low": percentage(low, total),
                "medium": percentage(medium, total),
                "high": percentage(high, total),
            }
            api_data.append(formatted_data)

        return api_data

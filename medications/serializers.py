import csv

from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

from .constants import field_rows


class CSVUploadSerializer(serializers.Serializer):
    csv_file = serializers.FileField()

    class Meta:
        fields = (
            'csv_file',
        )

    def is_valid(self, organization_id, raise_exception=False):
        if not organization_id:
            raise serializers.ValidationError(
                {'csv_file': _('This user has not organization related.')}
            )
        return super().is_valid(raise_exception)

    def validate(self, data):
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
                        'Wrong headers in CSV file, headers must be: {}'
                    ). format(', '.join(field_rows))}
            )
        return data

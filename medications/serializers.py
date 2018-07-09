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

    def validate(self, data):
        user = self.context.get('request').user
        if hasattr(user, 'organization'):
            organization = user.organization
        else:
            organization = None
        if not organization and not user.is_test:
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
                        'Wrong headers in CSV file, headers must be: {}. '
                    ). format(', '.join(field_rows))}
            )
        data['csv_file'] = file
        if not user.is_test:
            data['organization_id'] = organization.id
        else:
            data['organization_id'] = 0
        return data

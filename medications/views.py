from django.utils.translation import ugettext_lazy as _

from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from medications.tasks import generate_medications
from .serializers import CSVUploadSerializer
from .models import TemporaryFile


class CSVUploadView(GenericAPIView):
    serializer_class = CSVUploadSerializer
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        csv_file = serializer.validated_data.pop('csv_file')
        organization_id = serializer.validated_data.pop('organization_id')
        temporary_csv_file = TemporaryFile.objects.create(file=csv_file)
        generate_medications.delay(
            temporary_csv_file.id,
            organization_id,
        )
        # generate_medications(
        #     temporary_csv_file.id,
        #     organization_id,
        # ) 
        return Response(
            {'status': _('The medications creation proccess has been queued')},
            status=status.HTTP_200_OK,
        )

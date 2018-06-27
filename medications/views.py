from django.utils.translation import ugettext_lazy as _

from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response


from .serializers import CSVUploadSerializer
from .tasks import generate_medications


class CSVUploadView(GenericAPIView):
    parser_classes = (MultiPartParser,)
    serializer_class = CSVUploadSerializer

    def post(self, request, *args, **kwargs):
        if hasattr(request.user, 'organization'):
            organization_id = request.user.organization.id
        else:
            organization_id = None
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(organization_id, raise_exception=True)
        # generate_medications.delay(organization_id) Commented hust for testing
        generate_medications(organization_id) # Used without delay for testing purpose
        return Response(
            {'status': _('The medications creation proccess has been queued')},
            status=status.HTTP_200_OK,
        )

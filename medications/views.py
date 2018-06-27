from django.utils.translation import ugettext_lazy as _

from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response


from .serializers import CSVUploadSerializer


class CSVUploadView(GenericAPIView):
    parser_classes = (MultiPartParser,)
    serializer_class = CSVUploadSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        import pdb; pdb.set_trace()
        # TODO task.delay medications creation
        return Response(
            {'status': _('The medications creation proccess has been queued')},
            status=status.HTTP_200_OK,
        )

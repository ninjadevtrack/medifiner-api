from rest_framework.generics import GenericAPIView
from rest_framework.parsers import MultiPartParser


from .serializers import CSVUploadSerializer


class CSVUploadView(GenericAPIView):
    serializer_class = CSVUploadSerializer
    parser_classes = (MultiPartParser,)

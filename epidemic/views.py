from rest_framework.response import Response
from rest_framework.views import APIView

from epidemic.models import Epidemic


class EpidemicInfoView(APIView):

    def get(self, request):
        epidemic_status = Epidemic.objects.first().active
        return Response({'active': epidemic_status})

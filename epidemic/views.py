from rest_framework.response import Response
from rest_framework.views import APIView

from epidemic.models import Epidemic


class EpidemicInfoView(APIView):

    def get(self, request):
        alert_banner = Epidemic.objects.first()
        if not alert_banner.active:
            return Response({'active': False, 'content': ""})
        content = alert_banner.content
        return Response({'active': True, 'content': content})


from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import CSVUploadView, MedicationNameViewSet

router = DefaultRouter()
router.register(r'names', MedicationNameViewSet, base_name='name')

medications_api_urlpatterns = [
    path('csv_import', CSVUploadView.as_view()),
]

medications_api_urlpatterns += router.urls

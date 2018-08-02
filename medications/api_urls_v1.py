from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CSVUploadView,
    MedicationNameViewSet,
    StateViewSet,
    GeoStatsStatesWithMedicationsView,
    GeoStatsCountiesWithMedicationsView,
    GeoZipCodeWithMedicationsView,
)

router = DefaultRouter()
router.register(r'names', MedicationNameViewSet, base_name='name')
router.register(r'states', StateViewSet, base_name='state')

medications_api_urlpatterns = [
    path(
        'csv_import',
        CSVUploadView.as_view(),
    ),
    path(
        'geo_stats',
        GeoStatsStatesWithMedicationsView.as_view(),
    ),
    path(
        'geo_stats/state/<int:id>',
        GeoStatsCountiesWithMedicationsView.as_view(),
    ),
    path(
        'geo_stats/zipcode/<str:zipcode>',
        GeoZipCodeWithMedicationsView.as_view(),
    ),
]

medications_api_urlpatterns += router.urls

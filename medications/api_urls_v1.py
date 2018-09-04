from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CSVUploadView,
    CSVExportView,
    MedicationNameViewSet,
    StateViewSet,
    GeoStatsStatesWithMedicationsView,
    GeoStatsCountiesWithMedicationsView,
    GeoZipCodeWithMedicationsView,
    MedicationTypesView,
    OrganizationViewSet,
    ProviderTypesView,
    ProviderCategoriesView,
)

router = DefaultRouter()
router.register(
    r'names',
    MedicationNameViewSet,
    base_name='name',
)
router.register(
    r'states',
    StateViewSet,
    base_name='state',
)
router.register(
    r'organizations',
    OrganizationViewSet,
    base_name='organization',
)

medications_api_urlpatterns = [
    path(
        'csv_import/',
        CSVUploadView.as_view(),
    ),
    path(
        'geo_stats/',
        GeoStatsStatesWithMedicationsView.as_view(),
    ),
    path(
        'geo_stats/state/<int:state_id>/',
        GeoStatsCountiesWithMedicationsView.as_view(),
    ),
    path(
        'geo_stats/zipcode/<str:zipcode>/',
        GeoZipCodeWithMedicationsView.as_view(),
    ),
    path(
        'csv_export/',
        CSVExportView.as_view(),
    ),
    path(
        'csv_export/state/<int:state_id>/',
        CSVExportView.as_view(),
    ),
    path(
        'csv_export/zipcode/<str:zipcode>/',
        CSVExportView.as_view(),
    ),
    path(
        'provider_types/',
        ProviderTypesView.as_view(),
    ),
    path(
        'provider_categories/',
        ProviderCategoriesView.as_view(),
    ),
    path(
        'types/',
        MedicationTypesView.as_view(),
    ),
]

medications_api_urlpatterns += router.urls

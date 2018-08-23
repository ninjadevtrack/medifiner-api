from django.urls import path

from .views import (
    FindProviderMedicationView,
    BasicInfoView,
)

public_api_urlpatterns = [
    path(
        'find_providers/',
        FindProviderMedicationView.as_view(),
    ),
    path(
        'basic_info/',
        BasicInfoView.as_view(),
    ),
]

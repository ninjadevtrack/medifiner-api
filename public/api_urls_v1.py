from django.urls import path

from .views import (
    FindProviderMedicationView,
)

public_api_urlpatterns = [
    path(
        'find_providers/',
        FindProviderMedicationView.as_view(),
    ),
]

from django.urls import path

from .views import (
    FindProviderMedicationView,
    BasicInfoView,
    ContactFormView,
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
    path(
        'contact_form/',
        ContactFormView.as_view(),
    ),
]

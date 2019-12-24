from django.urls import path

from .views import (
    BasicInfoView,
    ContactFormView,
    FindProviderMedicationView,
    GetFormOptionsView,
)

public_api_urlpatterns = [
    path(
        'options/',
        GetFormOptionsView.as_view(),
    ),
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

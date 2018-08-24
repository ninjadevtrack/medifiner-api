from django.urls import path

from .views import (
    HistoricAverageNationalLevelView,
)

historic_api_urlpatterns = [
    path(
        'average/',
        HistoricAverageNationalLevelView.as_view(),
    ),
]

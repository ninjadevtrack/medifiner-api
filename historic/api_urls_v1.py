from django.urls import path

from .views import (
    HistoricAverageNationalLevelView,
    HistoricAverageStateLevelView,
    HistoricAverageZipCodeLevelView,
)

historic_api_urlpatterns = [
    path(
        'average/',
        HistoricAverageNationalLevelView.as_view(),
    ),
    path(
        'average/state/<int:state_id>/',
        HistoricAverageStateLevelView.as_view(),
    ),
    path(
        'average/zipcode/<str:zipcode>/',
        HistoricAverageZipCodeLevelView.as_view(),
    ),
]

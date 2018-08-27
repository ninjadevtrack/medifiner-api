from django.urls import path

from .views import (
    HistoricAverageNationalLevelView,
    HistoricAverageStateLevelView,
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
]

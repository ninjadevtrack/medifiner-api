from django.urls import path

from .views import (
    HistoricAverageView,
    HistoricOverallView,
)

historic_api_urlpatterns = [
    path(
        'average/',
        HistoricAverageView.as_view(),
    ),
    path(
        'average/state/<int:state_id>/',
        HistoricAverageView.as_view(),
    ),
    path(
        'average/zipcode/<str:zipcode>/',
        HistoricAverageView.as_view(),
    ),
    path(
        'overall/',
        HistoricOverallView.as_view(),
    ),
    path(
        'overall/state/<int:state_id>/',
        HistoricOverallView.as_view(),
    ),
    path(
        'overall/zipcode/<str:zipcode>/',
        HistoricOverallView.as_view(),
    ),
]

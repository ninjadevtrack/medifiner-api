from django.urls import path

from .views import CSVUploadView

medications_api_urlpatterns = [
    path('/', CSVUploadView.as_view()),
]

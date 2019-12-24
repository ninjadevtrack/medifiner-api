from django.urls import path

from .views import (
    SignInView,
)

accounts_api_urlpatterns = [
    path(
        'sign_in/',
        SignInView.as_view(),
        name='sign-in'
    ),
]

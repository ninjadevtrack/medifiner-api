from django.conf import settings
from django.urls import include, path
from django.contrib import admin
from django.conf.urls.static import static
from rest_framework_swagger.views import get_swagger_view
from rest_framework_jwt.views import ObtainJSONWebToken
from rest_registration.api.views import (
    send_reset_password_link,
    reset_password,
    profile,
)

from medications.api_urls_v1 import medications_api_urlpatterns
from auth_ex.api_urls_v1 import accounts_api_urlpatterns
from auth_ex.serializers import JSONWebTokenSerializer
from public.api_urls_v1 import public_api_urlpatterns
from historic.api_urls_v1 import historic_api_urlpatterns

from epidemic.views import EpidemicInfoView


schema_view = get_swagger_view(title='MedFinder API')

api_urlpatterns = [
    path(
        'accounts/',
        include(accounts_api_urlpatterns),
    ),
    path(
        'accounts/obtain_token/',
        ObtainJSONWebToken.as_view(serializer_class=JSONWebTokenSerializer),
        name='obtain-token',
    ),
    path(
        'accounts/profile/',
        profile,
        name='profile',
    ),
    path(
        'accounts/send-reset-password-link/',
        send_reset_password_link,
        name='send-reset-password-link',
    ),
    path(
        'accounts/reset-password/',
        reset_password,
        name='reset-password',
    ),
    path(
        'medications/',
        include(medications_api_urlpatterns),
    ),
    path(
        'public/',
        include(public_api_urlpatterns),
    ),
    path(
        'historic/',
        include(historic_api_urlpatterns),
    ),
    path(
        'epidemic/',
        EpidemicInfoView.as_view(),
    ),
]


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/swagger/', schema_view, name='swagger'),
    path('api/v1/', include(api_urlpatterns)),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )

"""
URL settings for debug_toolbar if instaled.
"""

if settings.ENABLE_DEBUG_TOOLBAR:
    import debug_toolbar
    urlpatterns += [
        path(r'^__debug__/', include(debug_toolbar.urls)),
    ]

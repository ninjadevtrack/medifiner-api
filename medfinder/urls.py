from django.conf import settings
from django.urls import include, path
from django.contrib import admin


api_urlpatterns = [
    path('accounts/', include('rest_registration.api.urls')),
]

urlpatterns = [
    path(r'admin/', admin.site.urls),
    path('api/v1/', include(api_urlpatterns)),
]

"""
URL settings for debug_toolbar if instaled.
"""

if settings.ENABLE_DEBUG_TOOLBAR:
    import debug_toolbar
    urlpatterns += [
        path(r'^__debug__/', include(debug_toolbar.urls)),
    ]

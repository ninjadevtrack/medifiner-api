from django.contrib import admin

from .models import Organization, Provider

admin.site.register(Organization)
admin.site.register(Provider)

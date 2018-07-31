from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from .models import (
    County,
    ExistingMedication,
    Medication,
    MedicationName,
    Organization,
    Provider,
    ProviderMedicationThrough,
    State,
    ZipCode,
)


@admin.register(ProviderMedicationThrough)
class ProviderMedicationThroughAdmin(admin.ModelAdmin):

    list_display = (
        '__str__',
        'date',
        'latest',
        'level',
    )
    list_filter = (
        'level',
    )
    readonly_fields = (
        'level',
        'date',
    )


@admin.register(State)
class StateAdmin(admin.ModelAdmin):

    list_display = (
        'state_name',
        'display_state_code',
        'state_us_id',
    )
    fields = (
        'display_state_code',
        'state_name',
        'state_us_id',
        'geometry',
    )
    readonly_fields = (
        'display_state_code',
        'state_name',
        'geometry',
        'state_us_id'
    )
    search_fields = (
        'state_name',
        'state_code',
    )

    def display_state_code(self, obj):
        return obj.state_code

    display_state_code.short_description = _('state code')


@admin.register(ZipCode)
class ZipCodeAdmin(admin.ModelAdmin):

    readonly_fields = (
        'zipcode',
        'state',
        'county',
        'geometry',
    )
    list_filter = (
        'state',
    )
    search_fields = (
        'zipcode',
        'state__state_name',
        'state__state_code',
        'county__county_name',
    )


@admin.register(County)
class CountyAdmin(admin.ModelAdmin):

    list_display = (
        'county_name',
        'state',
    )
    list_filter = (
        'state',
    )
    fields = (
        'county_name',
        'state',
        'county_name_slug',
        'geometry',
    )
    readonly_fields = (
        'county_name',
        'state',
        'geometry',
    )
    search_fields = (
        'county_name',
        'state__state_name',
        'state__state_code',
    )


@admin.register(ExistingMedication)
class ExistingMedicationAdmin(admin.ModelAdmin):

    list_display = (
        'ndc',
        'import_date',
        'description',
    )
    readonly_fields = (
        'import_date',
    )
    search_fields = (
        'ndc',
        'description',
    )


@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'ndc',
        'medication_name',
    )
    readonly_fields = (
        'ndc',
    )

    search_fields = (
        'ndc',
        'name',
    )
    list_filter = (
        'medication_name',
    )


@admin.register(MedicationName)
class MedicationName(admin.ModelAdmin):
    list_display = (
        'name',
    )
    search_fields = (
        'name',
    )


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = (
        'organization_name',
        'phone',
        'user',
        'registration_date'
    )

    search_fields = (
        'organization_name',
        'contact_name',
        'user',
    )


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = (
        '_name',
        'store_number',
        'organization',
        'type',
        'phone',
        'zip',
        'state',
        'full_address',
    )
    list_display_links = (
        'store_number',
        '_name',
    )
    list_filter = (
        'type',
        'related_zipcode__state',
    )
    search_fields = (
        'name',
        'store_number',
        'organization',
        'full_address',
    )

    def _name(self, obj):
        if obj.name:
            return obj.name
        return obj

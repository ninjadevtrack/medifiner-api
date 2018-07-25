from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from .models import (
    Organization,
    Provider,
    Medication,
    ProviderMedicationThrough,
    ExistingMedication,
    County,
    State,
    ZipCode,
)


@admin.register(ProviderMedicationThrough)
class ProviderMedicationThroughAdmin(admin.ModelAdmin):

    model = ProviderMedicationThrough
    list_display = ('__str__', 'date', 'latest', 'level')
    readonly_fields = (
        'level',
        'date',
    )


@admin.register(State)
class StateAdmin(admin.ModelAdmin):

    model = State
    list_display = ('state_name', 'display_state_code', 'state_us_id')
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
    search_fields = ('state_name', 'state_code')

    def display_state_code(self, obj):
        return obj.state_code

    display_state_code.short_description = _('state code')


@admin.register(ZipCode)
class ZipCodeAdmin(admin.ModelAdmin):
    model = ZipCode
    readonly_fields = (
        'zipcode',
        'state',
        'geometry',
    )
    search_fields = (
        'zipcode',
        'state__state_name',
        'state__state_code',
    )


@admin.register(County)
class CountyAdmin(admin.ModelAdmin):

    model = County
    list_display = ('county_name', 'state',)
    fields = (
        'county_name',
        'state',
        'geometry',
    )
    readonly_fields = (
        'county_name',
        'state',
        'geometry',
    )
    search_fields = ('county_name', 'state__state_name', 'state__state_code')


@admin.register(ExistingMedication)
class ExistingMedicationAdmin(admin.ModelAdmin):
    model = ExistingMedication
    search_fields = ('ndc', 'description')
    readonly_fields = ('import_date', )
    list_display = ('ndc', 'import_date', 'description')


admin.site.register(Organization)
admin.site.register(Provider)
admin.site.register(Medication)

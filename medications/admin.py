from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from .models import (
    Organization,
    Provider,
    Medication,
    ProviderMedicationThrough,
    ExistingMedication,
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
    list_display = ('state_name', 'display_state_code')
    fields = (
        'display_state_code',
        'state_name',
        'geometry',
    )
    readonly_fields = (
        'display_state_code',
        'state_name',
        'geometry',
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


@admin.register(ExistingMedication)
class ExistingMedicationAdmin(admin.ModelAdmin):
    model = ExistingMedication
    search_fields = ('ndc', 'description')
    readonly_fields = ('import_date', )
    list_display = ('ndc', 'import_date', 'description')


admin.site.register(Organization)
admin.site.register(Provider)
admin.site.register(Medication)

from django.contrib import admin

from .models import (
    Organization,
    Provider,
    Medication,
    ProviderMedicationThrough,
    ExistingMedication,
)


@admin.register(ProviderMedicationThrough)
class ProviderMedicationThroughAdmin(admin.ModelAdmin):

    model = ProviderMedicationThrough
    readonly_fields = (
        'level',
        'date',
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

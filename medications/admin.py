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


admin.site.register(Organization)
admin.site.register(Provider)
admin.site.register(Medication)
admin.site.register(ExistingMedication)

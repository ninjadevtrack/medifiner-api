from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from .forms import ProviderAdminForm
from .models import (
    County,
    ExistingMedication,
    Medication,
    MedicationName,
    MedicationNdc,
    Organization,
    Provider,
    ProviderMedicationNdcThrough,
    ProviderType,
    ProviderCategory,
    State,
    ZipCode,
)


@admin.register(ProviderMedicationNdcThrough)
class ProviderMedicationNDCThroughAdmin(admin.ModelAdmin):

    list_display = (
        '__str__',
        'creation_date',
        'date',
        'latest',
        'level',
    )
    list_filter = (
        'level',
    )
    readonly_fields = (
        'level',
        'creation_date',
        'date',
    )
    search_fields = (
        'provider__name',
        'medication_ndc__ndc'
    )

    def get_queryset(self, request):
        return super().get_queryset(
            request
        ).select_related(
            'medication_ndc',
            'medication_ndc__medication',
            'provider',
        )


@admin.register(State)
class StateAdmin(admin.ModelAdmin):

    list_display = (
        'state_name',
        'display_state_code',
        'state_us_id',
        'population',
    )
    fields = (
        'display_state_code',
        'state_name',
        'population',
        'state_us_id',
        'geometry',
    )
    readonly_fields = (
        'display_state_code',
        'state_name',
        'population',
        'geometry',
        'state_us_id'
    )
    search_fields = (
        'state_name',
        'state_code',
        'state_us_id',
    )

    def display_state_code(self, obj):
        return obj.state_code

    display_state_code.short_description = _('state code')


@admin.register(ZipCode)
class ZipCodeAdmin(admin.ModelAdmin):

    list_display = (
        'zipcode',
        'state',
        'population',
    )

    readonly_fields = (
        'zipcode',
        'state',
        'counties',
        'population',
        'geometry',
    )
    list_filter = (
        'state',
    )
    search_fields = (
        'zipcode',
        'state__state_name',
        'state__state_code',
        'counties__county_name',
        'state__state_us_id',
    )


@admin.register(County)
class CountyAdmin(admin.ModelAdmin):

    list_display = (
        'county_name',
        'state',
        'county_id',
        'population',
    )
    list_filter = (
        'state',
    )
    fields = (
        'county_name',
        'state',
        'county_name_slug',
        'county_id',
        'population',
        'geo_id',
        'geometry',
    )
    readonly_fields = (
        'county_name',
        'state',
        'county_id',
        'population',
        'geo_id',
        'geometry',
    )
    search_fields = (
        'county_name',
        'state__state_name',
        'state__state_code',
        'county_id',
        'geo_id',
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
        'ndcs',
        'medication_name',
    )
    readonly_fields = (
        'ndcs',
    )

    search_fields = (
        'name',
        'ndc_codes__ndc',
    )
    list_filter = (
        'medication_name',
    )

    def ndcs(self, obj):
        return ", ".join([p.ndc for p in obj.ndc_codes.all()])

    def get_queryset(self, request):
        return super().get_queryset(
            request
        ).select_related(
            'medication_name',
        ).prefetch_related(
            'ndc_codes',
        )


@admin.register(MedicationName)
class MedicationName(admin.ModelAdmin):
    list_display = (
        'name',
    )
    search_fields = (
        'name',
    )


@admin.register(MedicationNdc)
class MedicationNDC(admin.ModelAdmin):
    list_display = (
        'medication',
        'ndc',
    )
    search_fields = (
        'medication__name',
        'ndc',
    )


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = (
        'organization_name',
        'phone',
        'registration_date'
    )

    search_fields = (
        'organization_name',
        'contact_name',
    )


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    form = ProviderAdminForm
    list_display = (
        '_name',
        'store_number',
        'organization',
        'type',
        'category',
        'phone',
        'zip',
        'state',
        'full_address',
        'active',
        'last_import_date',
    )
    readonly_fields = (
        'related_zipcode',
        'full_address',
        'active',
        'last_import_date',
    )
    list_display_links = (
        'store_number',
        '_name',
    )
    list_filter = (
        'type',
        'category',
        'active',
        'related_zipcode__state',
    )
    search_fields = (
        'name',
        'store_number',
        'address',
        'city',
        'zip',
        'organization__organization_name',
    )
    fieldsets = (
        (
            None,
            {'fields': (
                'organization',
                'store_number',
                'name',
                'type',
                'category',
                'active',
                'last_import_date',
            )
            }
        ),
        (
            _('Addres info'),
            {'fields': (
                'address',
                'city',
                'state',
                'zip',
                'related_zipcode',
                'relate_related_zipcode',
                'full_address',
                'phone',
                'website',
                'email',
            )
            }
        ),
        (
            _('Localization info'),
            {'fields': (
                'lat',
                'lng',
                'change_coordinates',
            )
            }
        ),
        (
            _('Additional info'),
            {'fields': (
                'operating_hours',
                'notes',
                'insurance_accepted',
                'start_date',
                'end_date',
                'walkins_accepted',
                'home_delivery',
                'home_delivery_info_url',
            )
            }
        ),
    )

    def _name(self, obj):
        if obj.name:
            return obj.name
        return obj

    def get_queryset(self, request):
        return super().get_queryset(
            request
        ).select_related(
            'category',
            'organization',
            'type',
        )


admin.site.register(ProviderType)
admin.site.register(ProviderCategory)

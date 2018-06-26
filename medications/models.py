from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from localflavor.us.models import USStateField, USZipCodeField
from phonenumber_field.modelfields import PhoneNumberField

from .utils import get_lat_lng


# In version 1.0 using hardcoded country, if future versions have
# other countries support, a new field in the model should be added
COUNTRY = 'United States'


class Organization(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name='organization',
        on_delete=models.SET_NULL,
        null=True,
    )
    contact_name = models.CharField(
        _('contact name'),
        max_length=255,
        blank=True,
    )
    organization_name = models.CharField(
        _('organization name'),
        max_length=255,
    )
    phone = PhoneNumberField(
        _('organization phone'),
        blank=True,
    )
    website = models.URLField(
        _('organization website'),
        max_length=255,
        blank=True,
    )
    registration_date = models.DateTimeField(
        _('registration_date'),
        default=timezone.now
    )

    class Meta:
        verbose_name = _('organization')
        verbose_name_plural = _('organizations')

    def __str__(self):
        return self.organization_name


class Provider(models.Model):
    organization = models.ForeignKey(
        Organization,
        related_name='providers',
        on_delete=models.SET_NULL,
        null=True,
    )
    store_number = models.PositiveIntegerField(
        _('store number'),
        default=0,
    )
    name = models.CharField(
        _('provider name'),
        max_length=255,
    )
    address = models.CharField(
        _('provider address'),
        max_length=255,
    )
    city = models.CharField(
        _('provider city'),
        max_length=255,
    )
    state = USStateField(
        _('us state'),
    )
    zip = USZipCodeField(
        _('zip code'),
    )
    phone = PhoneNumberField(
        _('provider phone'),
    )
    website = models.URLField(
        _('provider website'),
        max_length=255,
        blank=True,
    )
    email = models.EmailField(
        _('provider email address'),
        unique=True,
        error_messages={
            'unique': 'A provider with that email already exists.',
        },
    )
    operating_hours = models.CharField(
        _('operating hours'),
        max_length=255,
        blank=True,
    )
    notes = models.TextField(
        _('notes'),
        blank=True,
    )
    insurance_accepted = models.TextField(
        _('insurance accepted'),
        blank=True,
    )
    lat = models.DecimalField(
        _('latitude'),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    lng = models.DecimalField(
        _('longitude'),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    change_coordinates = models.BooleanField(
        _('change coordinates'),
        default=False,
        help_text=_(
            'Check this if you want the application to recalculate the'
            ' coordinates. Used in case address has been changed'
        ),
    )
    start_date = models.DateTimeField(
        _('start date'),
        null=True,
        blank=True,
    )
    end_date = models.DateTimeField(
        _('start date'),
        null=True,
        blank=True,
    )
    # TODO: field 'type', is it choices? what's that?
    walkins_accepted = models.NullBooleanField(
        _('walkins accepted'),
    )

    class Meta:
        verbose_name = _('provider')
        verbose_name_plural = _('providers')

    def __str__(self):
        return self.name

    # Geocode using full address
    def _get_full_address(self):
        return '{} {} {} {} {}'.format(
            self.address,
            self.city,
            self.state,
            COUNTRY,
            self.zip,
        )
    full_address = property(_get_full_address)

    def save(self, *args, **kwargs):
        if self.change_coordinates:
            location = '+'.join(
                filter(
                    None,
                    (
                        self.address,
                        self.city,
                        self.state,
                        COUNTRY,
                    )
                )
            )
            self.lat, self.lng = get_lat_lng(location)
            self.change_coordinates = False
        super().save(*args, **kwargs)


class Medication(models.Model):
    name = models.CharField(
        _('medication name'),
        max_length=255,
    )
    ndc = models.CharField(
        _('national drug code'),
        max_length=32,
        unique=True,
    )

    class Meta:
        verbose_name = _('medication')
        verbose_name_plural = _('medications')

    def __str__(self):
        return self.name


class ProviderMedicationThrough(models.Model):
    provider = models.ForeignKey(
        Provider,
        related_name='provider_medication',
        on_delete=models.CASCADE,
    )
    medication = models.ForeignKey(
        Medication,
        related_name='provider_medication',
        on_delete=models.CASCADE,
    )
    supply = models.CharField(
        _('medication supply'),
        max_length=32,
    )
    level = models.PositiveIntegerField(
        _('medication level'),
        default=0,
    )
    start_date = models.DateTimeField(
        _('date'),
        auto_now_add=True,
    )

    class Meta:
        verbose_name = _('provider medication relation')
        verbose_name_plural = _('provider medication relations')

    def __str__(self):
        return '{} - {}'.format(self.provider, self.medication)

    def save(self, *args, **kwargs):
        # TODO: supply to level ampping
        super().save(*args, **kwargs)

from django.db import models
from django.conf import settings
from django.utils import timezone

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
        'contact name',
        max_length=255,
        blank=True,
    )
    organization_name = models.CharField(
        'organization name',
        max_length=255,
    )
    phone = PhoneNumberField(
        'organization phone',
        blank=True,
    )
    website = models.URLField(
        'organization website',
        max_length=255,
        blank=True,
    )
    registration_date = models.DateTimeField(
        'registration_date',
        default=timezone.now
    )

    class Meta:
        verbose_name = 'organization'
        verbose_name_plural = 'organizations'


class Provider(models.Model):
    organization = models.ForeignKey(
        Organization,
        related_name='providers',
        on_delete=models.SET_NULL,
        null=True,
    )
    store_number = models.PositiveIntegerField(
        'store number',
        default=0,
    )
    name = models.CharField(
        'name',
        max_length=255,
    )
    address = models.CharField(
        'address',
        max_length=255,
    )
    city = models.CharField(
        'city',
        max_length=255,
    )
    state = USStateField(
        'us state',
    )
    zip = USZipCodeField(
        'zip code',
    )
    phone = PhoneNumberField(
        'provider phone',
    )
    website = models.URLField(
        'provider website',
        max_length=255,
        blank=True,
    )
    email = models.EmailField(
        'provider email address',
        unique=True,
        error_messages={
            'unique': 'A provider with that email already exists.',
        },
    )
    operating_hours = models.CharField(
        'operating hours',
        max_length=255,
        blank=True,
    )
    notes = models.TextField(
        'notes',
        blank=True,
    )
    insurance_accepted = models.TextField(
        'insurance accepted',
        blank=True,
    )
    lat = models.DecimalField(
        'latitude',
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    lng = models.DecimalField(
        'longitude',
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    change_coordinates = models.BooleanField(
        'change coordinates',
        default=False,
        help_text='Check this if you want the application to recalculate the'
                  ' coordinates. Used in case address has been changed',
    )
    start_date = models.DateTimeField(
        'start date',
        null=True,
        blank=True,
    )
    end_date = models.DateTimeField(
        'start date',
        null=True,
        blank=True,
    )
    # TODO: field 'type', is it choices? what's that?
    walkins_accepted = models.NullBooleanField(
        'walkins accepted',
    )

    class Meta:
        verbose_name = 'provider'
        verbose_name_plural = 'providers'

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

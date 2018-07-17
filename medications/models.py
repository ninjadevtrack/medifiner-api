from django.db import models
from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from localflavor.us.models import USStateField, USZipCodeField

from phonenumber_field.modelfields import PhoneNumberField

from .utils import get_lat_lng
from .validators import validate_state, validate_zip


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
        default=None,
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


class State(models.Model):
    state = USStateField(
        _('us state'),
        validators=[validate_state],
    )
    geometry = JSONField(
        _('geometry'),
        default=dict,
    )

    class Meta:
        verbose_name = _('state')
        verbose_name_plural = _('states')

    def __str__(self):
        return self.state


class ZipCode(models.Model):
    zipcode = USZipCodeField(
        _('zip code'),
        validators=[validate_zip],
    )
    state = models.ForeignKey(
        State,
        related_name='zipcodes',
        on_delete=models.CASCADE,
    )
    geometry = JSONField(
        _('geometry'),
        default=dict,
    )

    class Meta:
        verbose_name = _('zip code')
        verbose_name_plural = _('zip codes')

    def __str__(self):
        return '{} - {}'.format(self.zipcode, self.state)


class Provider(models.Model):
    TYPE_COMMUNITY_RETAIL = 're'
    TYPE_CLINIC = 'cl'
    TYPE_COMPOUNDING = 'co'
    TYPE_CHOICES = (
        (TYPE_COMMUNITY_RETAIL, _('Community/Retail')),
        (TYPE_CLINIC, _('Clinic')),
        (TYPE_COMPOUNDING, _('Compounding')),
    )

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
    type = models.CharField(
        _('provider type'),
        choices=TYPE_CHOICES,
        default=TYPE_COMMUNITY_RETAIL,
        max_length=2,
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
        validators=[validate_state],
    )
    zip = USZipCodeField(
        _('zip code'),
        validators=[validate_zip],
    )
    related_zipcode = models.ForeignKey(
        ZipCode,
        related_name='providers',
        on_delete=models.SET_NULL,
        null=True,
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
        null=True,
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
    insurance_accepted = models.BooleanField(
        _('insurance accepted'),
        default=False,
    )
    lat = models.DecimalField(
        _('latitude'),
        max_digits=20,
        decimal_places=18,
        null=True,
        blank=True
    )
    lng = models.DecimalField(
        _('longitude'),
        max_digits=20,
        decimal_places=18,
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
    walkins_accepted = models.NullBooleanField(
        _('walkins accepted'),
    )

    class Meta:
        verbose_name = _('provider')
        verbose_name_plural = _('providers')

    def __str__(self):
        return '{} - store number: {}'.format(
            self.name if self.name else 'provider',
            self.store_number,
        )

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
        if self.change_coordinates or not self.pk:
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
    date = models.DateTimeField(
        _('date'),
        auto_now_add=True,
        help_text=_('Creation date'),
    )
    latest = models.BooleanField(
        _('latest'),
        default=False,
    )

    class Meta:
        verbose_name = _('provider medication relation')
        verbose_name_plural = _('provider medication relations')

    def __str__(self):
        return '{} - {}'.format(self.provider, self.medication)

    def save(self, *args, **kwargs):
        # Using a simple map for now, according to the specs
        # TODO: We need to ask client if this can get more complicated.
        supply_to_level_map = {
            '<24': 1,
            '24': 2,
            '24-48': 3,
            '>48': 4,
        }
        self.level = supply_to_level_map.get(self.supply, 0)
        super().save(*args, **kwargs)


class ExistingMedication(models.Model):
    # Model for medication imported from the database.
    description = models.TextField(
        _('medication description'),
        blank=True,
    )
    ndc = models.CharField(
        _('national drug code'),
        max_length=32,
    )
    import_date = models.DateTimeField(
        _('import date'),
        auto_now_add=True,
        help_text=_(
            'Date of import from the national database of this medication'
        ),
    )

    class Meta:
        verbose_name = _('existing medication')
        verbose_name_plural = _('existing medications')

    def __str__(self):
        return self.ndc


class TemporaryFile(models.Model):
    # Since we cannot pass files to celery, and also cannot pass temporary
    # files to celery since the temporary python files are closed after the
    # request is finished, we have to create an object in our database with
    # the csv file and them make celery delete it.
    file = models.FileField()

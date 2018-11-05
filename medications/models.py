from datetime import datetime
from django.db import models, IntegrityError
from django.conf import settings
from django.contrib.gis.db.models import GeometryField, PointField
from django.contrib.gis.geos import Point
from django.core.exceptions import MultipleObjectsReturned
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _

from localflavor.us.models import USStateField, USZipCodeField

from phonenumber_field.modelfields import PhoneNumberField

from .utils import get_lat_lng
from .validators import validate_state, validate_zip


# In version 1.0 using hardcoded country, if future versions have
# other countries support, a new field in the model should be added
COUNTRY = 'United States'


class Organization(models.Model):
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
    state_code = USStateField(
        _('us state code'),
        validators=[validate_state],
        null=True,

    )
    state_name = models.CharField(
        _('us state name'),
        max_length=255,
        blank=True,
    )
    geometry = GeometryField(
        _('geometry'),
        null=True,
    )
    state_us_id = models.PositiveIntegerField(
        _('state us id'),
        null=True,
        unique=True,
    )
    population = models.PositiveIntegerField(
        _('population'),
        null=True,
    )

    class Meta:
        verbose_name = _('state')
        verbose_name_plural = _('states')

    def __str__(self):
        return '{} - {}'.format(self.state_code, self.state_name)


class County(models.Model):
    county_name = models.CharField(
        _('us county name'),
        max_length=255,
        blank=True,
    )
    county_name_slug = models.SlugField(
        _('us county name slug'),
        max_length=255,
        blank=True,
    )
    state = models.ForeignKey(
        State,
        related_name='counties',
        on_delete=models.CASCADE,
    )
    geometry = GeometryField(
        _('geometry'),
        null=True,
    )
    county_id = models.PositiveIntegerField(
        _('county us id'),
        null=True,
    )
    geo_id = models.PositiveIntegerField(
        _('geo id'),
        null=True,
    )
    population = models.PositiveIntegerField(
        _('population'),
        null=True,
    )

    class Meta:
        verbose_name = _('county')
        verbose_name_plural = _('counties')

    def __str__(self):
        return self.county_name

    def save(self, *args, **kwargs):
        if not self.county_name_slug and self.county_name:
            self.county_name_slug = slugify(self.county_name)
        super().save(*args, **kwargs)


class ZipCode(models.Model):
    zipcode = USZipCodeField(
        _('zip code'),
        validators=[validate_zip],
    )
    geometry = GeometryField(
        _('geometry'),
        null=True,
    )
    state = models.ForeignKey(
        State,
        related_name='state_zipcodes',
        on_delete=models.CASCADE,
    )
    counties = models.ManyToManyField(
        County,
        related_name='county_zipcodes',
    )
    population = models.PositiveIntegerField(
        _('population'),
        null=True,
    )

    class Meta:
        verbose_name = _('zip code')
        verbose_name_plural = _('zip codes')

    def __str__(self):
        return '{} - {}'.format(self.zipcode, self.state)


class ProviderType(models.Model):
    code = models.CharField(
        _('provider type code'),
        max_length=2,
        default='00',
        help_text=_(
            'code used by the NCPDP to identify the type of provider.'
            'This code is a charfield cause it should be 01, 02, 03... and '
            'no more than 2 digits'
        ),
    )
    name = models.CharField(
        _('type name'),
        max_length=255,
    )

    def __str__(self):
        return '{} - {}'.format(self.code, self.name)


class ProviderCategory(models.Model):
    code = models.CharField(
        _('provider category code'),
        max_length=2,
        default='00',
        help_text=_(
            'code used by the NCPDP to identify the category of provider.'
            'This code is a charfield cause it should be 01, 02, 03... and '
            'no more than 2 digits'
        ),
    )
    name = models.CharField(
        _('category name'),
        max_length=255,
    )

    class Meta:
        verbose_name = _('provider category')
        verbose_name_plural = _('provider categories')

    def __str__(self):
        return '{} - {}'.format(self.code, self.name)


class ActiveProviderManager(models.Manager):
    """Custom manager to return active providers."""

    def active(self):
        """Method to return active providers."""
        return self.get_queryset().filter(active=True)


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
    type = models.ForeignKey(
        ProviderType,
        related_name='providers',
        on_delete=models.SET_NULL,
        null=True,
    )
    category = models.ForeignKey(
        ProviderCategory,
        related_name='providers',
        on_delete=models.SET_NULL,
        null=True,
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
    relate_related_zipcode = models.BooleanField(
        _('relate zipcode'),
        default=False,
        help_text=_(
            'Check if you need the system to relate a new zipcode object'
            ' to this provider. Generally you should use this only if you'
            ' are an admin changing the direction of this provider'
        ),
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
    lat = models.CharField(
        _('latitude'),
        blank=True,
        null=True,
        max_length=250,
    )
    lng = models.CharField(
        _('longitude'),
        blank=True,
        null=True,
        max_length=250,
    )
    geo_localization = PointField(
        _('localization'),
        null=True,
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
    last_import_date = models.DateTimeField(
        _('last import date'),
        auto_now_add=True,
        help_text=_(
            'Last time this provider uploaded new information.'
        ),
    )
    active = models.BooleanField(
        _('active'),
        default=True,
    )

    home_delivery = models.BooleanField(
        _('home delivery'),
        default=False,
    )

    home_delivery_info_url = models.URLField(
        _('home delivery info url'),
        max_length=255,
        blank=True,
    )

    objects = ActiveProviderManager()

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
            if self.lat and self.lng:
                self.geo_localization = Point(
                    float(self.lng),
                    float(self.lat),
                )
            self.change_coordinates = False
        if self.relate_related_zipcode and self.zip:
            zipcode = False
            try:
                zipcode = ZipCode.objects.get(
                    zipcode=self.zip[:5],
                    state__state_code=self.state,
                )
            except ZipCode.DoesNotExist:
                pass
            except MultipleObjectsReturned:
                zipcode = ZipCode.objects.filter(
                    zipcode=self.zip,
                    state__state_code=self.state,
                ).first()
            if zipcode:
                self.related_zipcode = zipcode
            self.relate_related_zipcode = False
        super().save(*args, **kwargs)


class MedicationName(models.Model):
    name = models.CharField(
        _('name'),
        max_length=255,
    )

    class Meta:
        verbose_name = _('medication name')
        verbose_name_plural = _('medication names')

    def __str__(self):
        return self.name


class Medication(models.Model):
    BRAND_DRUG = 'b'
    GENERIC_DRUG = 'g'
    PUBLIC_HEALTH_SUPPLY = 'p'
    DRUG_TYPE_CHOICES = (
        (BRAND_DRUG, _('Brand Drugs')),
        (GENERIC_DRUG, _('Generic Drugs')),
        (PUBLIC_HEALTH_SUPPLY, _('Public Health Supply')),
    )
    name = models.CharField(
        _('medication name'),
        max_length=255,
    )
    medication_name = models.ForeignKey(
        MedicationName,
        related_name='medications',
        on_delete=models.CASCADE,
        null=True,
    )
    drug_type = models.CharField(
        _('drug type'),
        max_length=1,
        choices=DRUG_TYPE_CHOICES,
        default=BRAND_DRUG,
    )

    class Meta:
        verbose_name = _('medication')
        verbose_name_plural = _('medications')

    def __str__(self):
        return self.name


class MedicationNdc(models.Model):
    medication = models.ForeignKey(
        Medication,
        related_name='ndc_codes',
        on_delete=models.CASCADE,
        null=True,
    )
    ndc = models.CharField(
        _('national drug code'),
        max_length=32,
        unique=True,
    )

    class Meta:
        verbose_name = _('medication NDC')
        verbose_name_plural = _('medication NDCs')
        indexes = [
            models.Index(fields=['ndc'])
        ]

    def __str__(self):
        return self.ndc


class ProviderMedicationNdcThrough(models.Model):
    provider = models.ForeignKey(
        Provider,
        related_name='provider_medication',
        on_delete=models.CASCADE,
    )
    medication_ndc = models.ForeignKey(
        MedicationNdc,
        related_name='provider_medication',
        on_delete=models.CASCADE,
        null=True,
    )
    supply = models.CharField(
        _('medication supply'),
        max_length=32,
        help_text=_(
            'Use one of the following strings to add a valide supply: '
            '<24, 24, 24-48, >48'
        ),
    )
    level = models.PositiveIntegerField(
        _('medication level'),
        default=0,
    )
    creation_date = models.DateTimeField(
        _('creation date'),
        help_text=_('Creation date'),
    )
    last_modified = models.DateTimeField(
        _('last modified date'),
        help_text=_('Last modification date'),
    )
    latest = models.BooleanField(
        _('latest'),
        default=False,
    )

    class Meta:
        verbose_name = _('provider medication relation')
        verbose_name_plural = _('provider medication relations')
        indexes = [
            models.Index(fields=['provider_id', 'medication_ndc_id', 'latest'])
        ]

    def __str__(self):
        if self.medication_ndc and hasattr(self.medication_ndc, 'medication'):
            medication = self.medication_ndc.medication
        else:
            medication = self.medication_ndc
        return '{} - {}'.format(self.provider, medication)

    def save(self, *args, **kwargs):
        # Using a simple map for now, according to the specs
        if not self.medication_ndc:
            raise IntegrityError(_('Medication NDC object must be provided'))
        if self.creation_date is None:
            self.creation_date = datetime.datetime.now()
        if self.last_modified is None:
            self.last_modified = datetime.datetime.now()
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

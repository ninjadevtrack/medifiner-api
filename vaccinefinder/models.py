from django.db import models
from django.conf import settings
from django.contrib.gis.db.models import GeometryField, PointField
from django.contrib.gis.geos import Point
from django.core.exceptions import MultipleObjectsReturned
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _

from localflavor.us.models import USStateField, USZipCodeField

from phonenumber_field.modelfields import PhoneNumberField


class Organization(models.Model):
    organization_id = models.AutoField(
        primary_key=True
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
    reg_date = models.DateTimeField(
        _('registration_date'),
        default=timezone.now
    )

    class Meta:
        db_table = 'organization'
        verbose_name = _('organization')
        verbose_name_plural = _('organizations')

    def __str__(self):
        return self.organization_name


class Provider(models.Model):
    provider_id = models.AutoField(
        primary_key=True
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
    type = models.PositiveIntegerField(
        _('type'),
        default=0,
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
        blank=True,
        null=True,
        max_length=250,
    )
    lon = models.CharField(
        blank=True,
        null=True,
        max_length=250,
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
    home_delivery = models.NullBooleanField(
        _('home delivery'),
    )
    home_delivery_site = models.CharField(
        blank=True,
        null=True,
        max_length=250,
    )

    class Meta:
        db_table = 'provider'
        verbose_name = _('provider')
        verbose_name_plural = _('providers')

    def __str__(self):
        return '{} - store number: {}'.format(
            self.name if self.name else 'provider',
            self.store_number,
        )

from django.db import models
from django.conf import settings
from django.utils import timezone

from phonenumber_field.modelfields import PhoneNumberField


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
        'phone',
        blank=True,
    )
    website = models.URLField(
        'website',
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

    def __str__(self):
        return self.organization_name

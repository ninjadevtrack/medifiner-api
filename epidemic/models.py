from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _
from tinymce.models import HTMLField

class Epidemic(models.Model):
    active = models.BooleanField(
        _('active'),
        default=False,
        help_text=_(
            'Designates whether the flag Epidemic is active or not globally'
        )
    )

    content = HTMLField()

    class Meta:
        verbose_name = _('Alert Banner')
        verbose_name_plural = _('Alert Banner')

    def __str__(self):
        return 'Alert Banner'

    def save(self, *args, **kwargs):
        if Epidemic.objects.exists() and not self.pk:
            raise ValidationError('There is can be only one Epidemic instance')
        return super().save(*args, **kwargs)

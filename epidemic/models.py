from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _


class Epidemic(models.Model):
    active = models.BooleanField(
        _('active'),
        default=False,
        help_text=_(
            'Designates whether the flag Epidemic is active or not globally'
        )
    )

    class Meta:
        verbose_name = _('Epidemic')
        verbose_name_plural = _('Epidemic')

    def __str__(self):
        return 'Epidemic'

    def save(self, *args, **kwargs):
        if Epidemic.objects.exists() and not self.pk:
            raise ValidationError('There is can be only one Epidemic instance')
        return super().save(*args, **kwargs)

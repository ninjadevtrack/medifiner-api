from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from .models import Provider, State, ZipCode


class ProviderAdminForm(forms.ModelForm):

    class Meta:
        model = Provider
        exclude = ()

    def clean(self):
        state = self.cleaned_data.get('state')
        zipcode = self.cleaned_data.get('zip')
        if not State.objects.filter(state_code=state).exists():
            raise ValidationError(
                {'state': _('You have selected an invalid state')}
            )
        try:
            ZipCode.objects.get(
                zipcode=zipcode,
                state__state_code=state,
            )
        except ZipCode.DoesNotExist:
            raise ValidationError(
                {'zip': _(
                    'You have entered a zipcode that does not belong to the'
                    ' selected state or just does not exist in the database'
                )
                }
            )
        return self.cleaned_data

import re

from django.utils.translation import ugettext_lazy as _
from localflavor.us.us_states import USPS_CHOICES
from django.core.exceptions import ValidationError


def validate_state(value):
    states_list = [code[0] for code in USPS_CHOICES]
    if value not in states_list:
        raise ValidationError(_('The selected state is not a US state.'))


def validate_zip(value):
    pattern = re.compile(r'^\d{5}(?:-\d{4})?$')
    if not bool(pattern.match(value)):
        raise ValidationError(_('The used code is not a US zip code.'))

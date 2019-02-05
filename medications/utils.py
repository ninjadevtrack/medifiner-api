import json as simplejson

from django.conf import settings
from django.utils.encoding import smart_str
from urllib.parse import quote_plus
from urllib.request import urlopen

from django.utils.translation import ugettext_lazy as _
from rest_registration.exceptions import BadRequest


def get_lat_lng(location):
    # Helper method to geocode address using Google Geocoder
    # Reference: http://djangosnippets.org/snippets/293/

    location = quote_plus(smart_str(location))
    url = 'https://maps.googleapis.com/maps/api/geocode/json?address={}&sensor=false&key={}'.format(  # noqa
        location,
        settings.GOOGLE_MAP_API_KEY,
    )
    response = urlopen(url).read()
    result = simplejson.loads(response)
    if result['status'] == 'OK':
        try:
            lat = str(result['results'][0]['geometry']['location']['lat'])
            lng = str(result['results'][0]['geometry']['location']['lng'])
            return (lat, lng)
        except (IndexError, KeyError):
            return (None, None)
    else:
        return (None, None)


def get_dominant_supply(noreport, nosupply, low, medium, high, total):
    if total:
        if nosupply / total > 0.85:
            return 'nosupply'
        if high / total > 0.85:
            return 'high'
        elif (high / total + medium / total) > 0.85:
            return 'medium'
        else:
            return 'low'
    return None


def get_supplies(supply_levels):
    noreport = 0
    nosupply = 0
    low = 0
    medium = 0
    high = 0
    for level in supply_levels:
        if level == -1:
            noreport += 1
        if level == 0:
            nosupply += 1
        if level == 1:
            low += 1
        elif level == 2 or level == 3:
            medium += 1
        elif level == 4:
            high += 1
    dominant = get_dominant_supply(
        noreport,
        nosupply,
        low,
        medium,
        high,
        nosupply + low + medium + high,
    )
    return {'nosupply': nosupply, 'low': low, 'medium': medium, 'high': high}, dominant


def force_user_state_id_and_zipcode(user, state_id, zipcode):
    from medications.models import ZipCode

    if user.permission_level == user.STATE_LEVEL:
        if not user.state_id or (zipcode and ZipCode.objects.filter(zipcode=zipcode, state_id=user.state_id).count() == 0):
            msg = _('Permission denied - Please check with system administrator')
            raise BadRequest(msg)
        return user.state_id, zipcode
    return state_id, zipcode

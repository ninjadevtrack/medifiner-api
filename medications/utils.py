import json as simplejson

from urllib.request import urlopen
from urllib.parse import quote_plus
from django.utils.encoding import smart_str


def get_lat_lng(location):
    # Helper method to geocode address using Google Geocoder
    # Reference: http://djangosnippets.org/snippets/293/

    location = quote_plus(smart_str(location))
    url = 'http://maps.googleapis.com/maps/api/geocode/json?address={}&sensor=false'.format(location)
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


def get_dominant_supply(low, medium, high ,total):
    if total:
        if high / total > 0.85:
            return 'high'
        elif (high / total + medium / total) > 0.85:
            return 'medium'
        else:
            return 'low'
    return None


def get_supplies(supply_levels):
    low = 0
    medium = 0
    high = 0
    for level in supply_levels:
        if level == 1:
            low += 1
        elif level == 2 or level == 3:
            medium += 1
        elif level == 4:
            high += 1
    dominant = get_dominant_supply(
        low,
        medium,
        high,
        low + medium + high,
    )
    return {'low': low, 'medium': medium, 'high': high}, dominant

def get_center_point(data):
    points = []
    for feature in data:
        feature['geometry']

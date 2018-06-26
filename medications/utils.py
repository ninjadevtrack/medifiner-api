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
        lat = str(result['results'][0]['geometry']['location']['lat'])
        lng = str(result['results'][0]['geometry']['location']['lng'])
        return (lat, lng)
    else:
        return (None, None)

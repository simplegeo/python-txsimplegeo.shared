API_VERSION = '1.0'

__all__ = []

from _version import __version__
__version__ # hush pyflakes

from zope.interface import implements

from twisted.web.client import Agent, ResponseDone
from twisted.web.iweb import IBodyProducer
from twisted.python.failure import Failure
from twisted.internet import reactor
from twisted.internet.protocol import Protocol
from twisted.internet.defer import Deferred, succeed

import copy, re
from decimal import Decimal as D

from urlparse import urljoin

from pyutil import jsonutil as json
from pyutil.assertutil import precondition

# example: http://api.simplegeo.com/1.0/feature/abcdefghijklmnopqrstuvwyz.json

def json_decode(jsonstr):
    try:
        return json.loads(jsonstr)
    except (ValueError, TypeError), le:
        raise DecodeError(jsonstr, le)

def swap(tupleab):
    return (tupleab[1], tupleab[0])

def deep_swap(struc):
    if is_numeric(struc[0]):
        assert len(struc) == 2
        assert is_numeric(struc[1])
        return swap(struc)
    return [deep_swap(sub) for sub in struc]

def deep_validate_lat_lon(struc):
    precondition(isinstance(struc, (list, tuple, set)), 'argument must be a sequence (of sequences of...) numbers')
    if is_numeric(struc[0]):
        assert len(struc) == 2
        assert is_numeric(struc[1])
        assert is_valid_lat(struc[0])
        assert is_valid_lon(struc[1])
    else:
        for sub in struc:
            deep_validate_lat_lon(sub)
    return True

SIMPLEGEOHANDLE_RSTR=r"""SG_[A-Za-z0-9]{22}(?:_-?[0-9]{1,3}(?:\.[0-9]+)?_-?[0-9]{1,3}(?:\.[0-9]+)?)?(?:@[0-9]+)?$"""
SIMPLEGEOHANDLE_R= re.compile(SIMPLEGEOHANDLE_RSTR)
def is_simplegeohandle(s):
    return isinstance(s, basestring) and SIMPLEGEOHANDLE_R.match(s)

FEATURES_URL_R=re.compile("http://(.*)/features/([A-Za-z_,-]*).json$")

def is_numeric(x):
    return isinstance(x, (int, long, float, D))

def is_valid_lat(x):
    return is_numeric(x) and (x <= 90) and (x >= -90)

def is_valid_lon(x):
    return is_numeric(x) and (x <= 180) and (x >= -180.0)

class Feature:
    def __init__(self, coordinates, geomtype='Point', simplegeohandle=None, properties=None):
        """
        The simplegeohandle and the record_id are both optional -- you
        can have one or the other or both or neither.

        A simplegeohandle is globally unique and is assigned by the
        Places service. It is returned from the Places service in the
        response to a request to add a place to the Places database
        (the add_feature method).

        The simplegeohandle is passed in as an argument to the
        constructor, named "simplegeohandle", and is stored in the
        "id" attribute of the Feature instance.

        A record_id is scoped to your particular user account and is
        chosen by you. The only use for the record_id is in case you
        call add_feature and you have already previously added that
        feature to the database -- if there is already a feature from
        your user account with the same record_id then the Places
        service will return that feature to you, along with that
        feature's simplegeohandle, instead of making a second, duplicate
        feature.

        A record_id is passed in as a value in the properties dict
        named "record_id".

        geomtype is a GeoJSON geometry type such as "Point",
        "Polygon", or "Multipolygon". coordinates is a GeoJSON
        coordinates *except* that each lat/lon pair is written in
        order lat, lon instead of the GeoJSON order of lon, at.

        When txsimplegeo.shared is constructing a Feature object from
        the result of an HTTP query to the SimpleGeo service, it will
        stash a reference to the twisted.web.client.Response object in
        the "._http_response" member variable of the Feature
        object. This could be useful for debugging, investigating the
        performance of the SimpleGeo service, etc.
        """
        precondition(simplegeohandle is None or is_simplegeohandle(simplegeohandle), "simplegeohandle is required to be None or to match the regex %s" % SIMPLEGEOHANDLE_RSTR, simplegeohandle=simplegeohandle)
        record_id = properties and properties.get('record_id') or None
        precondition(record_id is None or isinstance(record_id, basestring), "record_id is required to be None or a string.", record_id=record_id, properties=properties)
        precondition(deep_validate_lat_lon(coordinates), coordinates)

        self.id = simplegeohandle
        self.coordinates = coordinates
        self.geomtype = geomtype
        self.properties = {}
        if properties:
            self.properties.update(properties)

    @classmethod
    def from_dict(cls, data):
        """
        data is a GeoJSON standard data structure, including that the
        coordinates are in GeoJSON order (lon, lat) instead of
        SimpleGeo order (lat, lon)
        """
        assert isinstance(data, dict), (type(data), repr(data))
        feature = cls(
            simplegeohandle = data.get('id'),
            coordinates = deep_swap(data['geometry']['coordinates']),
            geomtype = data['geometry']['type'],
            properties = data.get('properties')
            )

        return feature

    def to_dict(self):
        """
        Returns a GeoJSON object, including having its coordinates in
        GeoJSON standad order (lon, lat) instead of SimpleGeo standard
        order (lat, lon).
        """
        return {
            'type': 'Feature',
            'id': self.id,
            'geometry': {
                'type': self.geomtype,
                'coordinates': deep_swap(self.coordinates)
            },
            'properties': copy.deepcopy(self.properties),
        }

    @classmethod
    def from_json(cls, jsonstr):
        return cls.from_dict(json_decode(jsonstr))

    def to_json(self):
        return json.dumps(self.to_dict())

class StringProducer(object):
    implements(IBodyProducer)
    """
    If you have a string that you want to pass as the body of your
    HTTP request, wrap it in an instance of StringProducer and pass
    that as the `body' argument of Agent.request().
    """
    def __init__(self, body):
        self.body = body
        self.length = len(body)

    def startProducing(self, consumer):
        consumer.write(self.body)
        return succeed(None)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass

class BodyCollector(Protocol):
    """
    If you want to accumulate the body of an HTTP response until it is
    all finished and then get the result in a string, then create an
    instance of BodyCollector, call its .start() method to get a
    deferred, and pass the instance of BodyCollector as the argument
    to Response.deliverBody(). When the deferred that it gave you
    calls your callback, it will pass the string containing the HTTP
    response body.
    """
    def __init__(self):
        self.finished = Deferred()
        self.bytesl = []

    def start(self):
        return self.finished

    def dataReceived(self, bytes):
        self.bytesl.append(bytes)

    def connectionLost(self, reason):
        self.reason = reason
        self.bytes = ''.join(self.bytesl)
        if isinstance(reason, ResponseDone):
            self.finished.callback(self)
        else:
            self.finished.errback(reason)

def get_body(resp):
    """
    Takes a Response object, returns a deferred that will eventually
    fire with the response body in a string, if the response indicates
    a 200 success.
    """
    bc = BodyCollector()

    resp.deliverBody(bc)

    def _collected(bc):
        return bc.bytes

    d = bc.start()
    d.addCallback(_collected)
    return d



class Client(object):
    realm = "http://api.simplegeo.com"
    endpoints = {
        'feature': 'features/%(simplegeohandle)s.json',
    }

    def __init__(self, key, secret, api_version=API_VERSION, host="api.simplegeo.com", port=80):
        self.host = host
        self.port = port
        self.key = key
        self.secret = secret
        self.api_version = api_version
        self.uri = "http://%s:%s" % (host, port)
        self.agent = Agent(reactor)

    def get_most_recent_http_headers(self):
        """ Intended for debugging -- return the most recent HTTP
        headers which were received from the server. """
        return self.headers

    def _endpoint(self, name, **kwargs):
        """Not used directly. Finds and formats the endpoints as needed for any type of request."""
        try:
            endpoint = self.endpoints[name]
        except KeyError:
            raise Exception('No endpoint named "%s"' % name)
        try:
            endpoint = endpoint % kwargs
        except KeyError, e:
            raise TypeError('Missing required argument "%s"' % (e.args[0],))
        return urljoin(urljoin(self.uri, self.api_version + '/'), endpoint)

    def get_feature(self, simplegeohandle):
        """
        Return the GeoJSON representation of a feature.

        Return a deferred which, if the request succeeds, eventually
        fires with the Feature object. If the request fails, the
        deferred instead errbacks with the twisted.web.client.Response
        object.
        """
        precondition(is_simplegeohandle(simplegeohandle), "simplegeohandle is required to match the regex %s" % SIMPLEGEOHANDLE_RSTR, simplegeohandle=simplegeohandle)
        endpoint = self._endpoint('feature', simplegeohandle=simplegeohandle)
        d = self._request(endpoint, 'GET')
        def _handle_resp(resp):
            if (resp.code / 100) not in (2, 3):
                return Failure(resp)

            d2 = get_body(resp)
            def _handle_body(body):
                f = Feature.from_json(body)
                f._http_response = resp
                return f

            d2.addCallback(_handle_body)
            return d2
        d.addCallback(_handle_resp)
        return d

    def _request(self, endpoint, method, data=None):
        """
        Not used directly by code external to this lib. Performs the
        actual request against the API, including passing the
        credentials with oauth.  Returns deferred that eventually
        fires with a twisted.web.client.Response instance.
        """
        if data is None:
            data = ''
        elif not isinstance(data, basestring):
            raise TypeError("data is required to be None or a string or unicode, not %s" % (type(data),))

        body = StringProducer(data)

# xyZ
#         # headers = request.to_header(self.realm)
#         headers = {}
#XXX         headers['User-Agent'] = 'SimpleGeo Places Client v%s' % __version__

        d = self.agent.request(method, endpoint, bodyProducer=body)

        # def _callb(resp):
        #     self.headers = resp.header
        #     if (resp.code / 100) not in ('2', '3'):
        #         raise APIError(int(self.headers['status']), content, self.headers)
# 
#             self.k
#             self.headers, content = self.http.request(endpoint, method, body=body, headers=headers)

        return d # XXX self.headers, content


class APIError(Exception):
    """Base exception for all API errors."""

    def __init__(self, code, msg, headers, description=''):
        self.code = code
        self.msg = msg
        self.headers = headers
        self.description = description

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return "%s (#%s) %s" % (self.msg, self.code, self.description)

class DecodeError(APIError):
    """There was a problem decoding the API's response, which was
    supposed to be encoded in JSON, but which apparently wasn't."""

    def __init__(self, body, le):
        super(DecodeError, self).__init__(None, "Could not decode JSON from server.", None, repr(le))
        self.body = body

    def __repr__(self):
        return "%s content: %s" % (self.description, self.body)

from twisted.trial import unittest
from twisted.internet import defer
from twisted.web.client import Response, ResponseDone
from twisted.web.http import PotentialDataLoss

from pyutil import jsonutil as json
from txsimplegeo.shared import BodyCollector, Client, DecodeError, Feature, StringProducer, get_body

from decimal import Decimal as D

MY_OAUTH_KEY = 'MY_OAUTH_KEY'
MY_OAUTH_SECRET = 'MY_SECRET_KEY'
TESTING_LAYER = 'TESTING_LAYER'

API_VERSION = '1.0'
API_HOST = 'api.simplegeo.com'
API_PORT = 80

class DecodeErrorTest(unittest.TestCase):
    def test_repr(self):
        body = 'this is not json'
        try:
            json.loads('this is not json')
        except ValueError, le:
            e = DecodeError(body, le)
        else:
            self.fail("We were supposed to get an exception from json.loads().")

        self.failUnless("Could not decode JSON" in e.msg, repr(e.msg))
        self.failUnless('JSONDecodeError' in repr(e), repr(e))

class FakeResponse(Response):
    def __init__(self, respchunks, headers, code):
        self.respchunks = respchunks
        self.headers = headers
        self.code = code

    def deliverBody(self, consumer):
        consumer.connectionLost(ResponseDone())

class FakeSuccessResponse(FakeResponse):
    def __init__(self, respchunks, headers):
        FakeResponse.__init__(self, respchunks, headers, code=200)

    def deliverBody(self, consumer):
        for respchunk in self.respchunks:
            consumer.dataReceived(respchunk)
        consumer.connectionLost(ResponseDone())

class FakePotentialDataLossResponse(FakeResponse):
    def deliverBody(self, consumer):
        for respchunk in self.respchunks:
            consumer.dataReceived(respchunk)
        consumer.connectionLost(PotentialDataLoss())

class SomeException(Exception):
    pass

class FakeExceptionResponse(FakeResponse):
    def deliverBody(self, consumer):
        for respchunk in self.respchunks:
            consumer.dataReceived(respchunk)
        consumer.connectionLost(PotentialDataLoss())

class FakeConsumer(object):
    def write(self, body):
        self.body = body

class MockAgent(object):
    def __init__(self, fakeresp):
        self.fakeresp = fakeresp

    def request(self, method, endpoint, bodyProducer):
        self.method = method
        self.endpoint = endpoint
        self.bodyProducer = bodyProducer
        return defer.succeed(self.fakeresp)

class StringProducerTest(unittest.TestCase):
    def test_string_producer(self):
        sp = StringProducer('abc')

        sp.pauseProducing()

        fc = FakeConsumer()
        sp.startProducing(fc)

        self.failUnlessEqual(fc.body, 'abc')

        sp.stopProducing()

class BodyCollectorTest(unittest.TestCase):
    def test_body_collector_collects_body(self):
        bc = BodyCollector()
        d = bc.start()
        bc.dataReceived('a')
        bc.dataReceived('b')
        bc.connectionLost(ResponseDone())
        def _check(res):
            self.failUnless(res is bc, (res, bc))
            self.failUnless(isinstance(res.reason, ResponseDone), (res.reason, type(res.reason)))
            self.failUnless(res.bytes == 'ab', res.bytes)
        d.addCallback(_check)
        return d

    def test_body_collector_errs_on_PotentialDataLoss(self):
        bc = BodyCollector()
        d = bc.start()
        bc.dataReceived('a')
        bc.dataReceived('b')
        bc.connectionLost(PotentialDataLoss())

        d1 = self.failUnlessFailure(d, PotentialDataLoss)
        return d1

    def test_get_body_gets_body(self):
        fakeresp = FakeSuccessResponse(['a', 'b'], {})

        d = get_body(fakeresp)
        def _check(res):
            self.failUnlessEqual(res, 'ab')
        d.addCallback(_check)
        return d

    def test_get_body_errs_on_PDL(self):
        fakeresp = FakePotentialDataLossResponse(['a', 'b'], {}, 200)

        d = get_body(fakeresp)
        d2 = self.failUnlessFailure(d, PotentialDataLoss)
        return d2

    def test_get_body_errs_on_exception(self):
        fakeresp = FakeExceptionResponse(['a', 'b'], {}, 200)

        d = get_body(fakeresp)
        d2 = self.failUnlessFailure(d, Exception)
        return d2

class ClientTest(unittest.TestCase):
    def setUp(self):
        self.client = Client(MY_OAUTH_KEY, MY_OAUTH_SECRET, API_VERSION, API_HOST, API_PORT)
        self.query_lat = D('37.8016')
        self.query_lon = D('-122.4783')

    def test_wrong_endpoint(self):
        self.assertRaises(Exception, self.client._endpoint, 'wrongwrong')

    def test_missing_argument(self):
        self.assertRaises(Exception, self.client._endpoint, 'feature')

    def test_get_point_feature(self):
        mockagent = MockAgent(FakeSuccessResponse([EXAMPLE_POINT_BODY], {'status': '200', 'content-type': 'application/json', 'thingie': "just to see if you're listening"}))
        self.client.agent = mockagent

        d = self.client.get_feature("SG_4bgzicKFmP89tQFGLGZYy0_34.714646_-86.584970")
        def check_res(res):
            self.assertEqual(mockagent.method, 'GET')
            self.assertEqual(mockagent.endpoint, 'http://api.simplegeo.com:80/%s/features/%s.json' % (API_VERSION, "SG_4bgzicKFmP89tQFGLGZYy0_34.714646_-86.584970"))
            # the code under test is required to have json-decoded this before handing it back
            self.failUnless(isinstance(res, Feature), (repr(res), type(res)))
            self.failUnlessEqual(res._http_response.headers, {'status': '200', 'content-type': 'application/json', 'thingie': "just to see if you're listening"})

        d.addCallback(check_res)
        return d

    def test_get_polygon_feature(self):
        mockagent = MockAgent(FakeSuccessResponse([EXAMPLE_BODY], {'status': '200', 'content-type': 'application/json'}))
        self.client.agent = mockagent

        d = self.client.get_feature("SG_4bgzicKFmP89tQFGLGZYy0_34.714646_-86.584970")
        def check_res(res):
            self.assertEqual(mockagent.method, 'GET')
            self.assertEqual(mockagent.endpoint, 'http://api.simplegeo.com:80/%s/features/%s.json' % (API_VERSION, "SG_4bgzicKFmP89tQFGLGZYy0_34.714646_-86.584970"))
            # the code under test is required to have json-decoded this before handing it back
            self.failUnless(isinstance(res, Feature), (repr(res), type(res)))

        d.addCallback(check_res)
        return d

    def test_type_check_request(self):
        self.failUnlessRaises(TypeError, self.client._request, 'whatever', 'POST', {'bogus': "non string"})

    def test_get_feature_bad_json(self):
        mockagent = MockAgent(FakeSuccessResponse([EXAMPLE_BODY, 'some crap'], {'status': '200', 'content-type': 'application/json'}))
        self.client.agent = mockagent

        d = self.client.get_feature("SG_4bgzicKFmP89tQFGLGZYy0_34.714646_-86.584970")
        self.failUnlessFailure(d, DecodeError)
        def after_error(f):
            self.assertEqual(mockagent.endpoint, 'http://api.simplegeo.com:80/%s/features/%s.json' % (API_VERSION, "SG_4bgzicKFmP89tQFGLGZYy0_34.714646_-86.584970"))
            self.assertEqual(mockagent.method, 'GET')

        d.addCallback(after_error)

        return d

    def test_dont_json_decode_results(self):
        """ _request() is required to return a deferred that fires
        with a Response that has a deliverBody that delivers the exact
        string that the HTTP server sent to it -- no transforming it,
        such as by json-decoding. """

        mockagent = MockAgent(FakeSuccessResponse(['{ "Hello": "I am a string. \xe2\x9d\xa4" }'.decode('utf-8')], {'status': '200', 'content-type': 'application/json'}))
        self.client.agent = mockagent

        d = self.client._request("http://thing", 'POST')
        d.addCallback(get_body)
        def _with_body(body):
            self.failUnlessEqual(body, '{ "Hello": "I am a string. \xe2\x9d\xa4" }'.decode('utf-8'))
        d.addCallback(_with_body)
        return d

    def test_dont_Recordify_results(self):
        """ _request() is required to return the exact string that the HTTP
        server sent to it -- no transforming it, such as by json-decoding and
        then constructing a Record. """

        EXAMPLE_RECORD_JSONSTR=json.dumps({ 'geometry' : { 'type' : 'Point', 'coordinates' : [D('10.0'), D('11.0')] }, 'id' : 'my_id', 'type' : 'Feature', 'properties' : { 'key' : 'value'  , 'type' : 'object' } })

        mockagent = MockAgent(FakeSuccessResponse([EXAMPLE_RECORD_JSONSTR], {'status': '200', 'content-type': 'application/json'}))
        self.client.agent = mockagent

        d = self.client._request("http://thing", 'POST')
        d.addCallback(get_body)
        def check(res):
            self.failUnlessEqual(res, EXAMPLE_RECORD_JSONSTR)
        d.addCallback(check)
        return d

    def test_get_feature_error(self):
        fakeresp = FakeResponse('{"message": "help my web server is confuzzled"}', {'status': '500', 'content-type': 'application/json'}, code=500)
        mockagent = MockAgent(fakeresp)
        self.client.agent = mockagent

        d = self.client.get_feature("SG_4bgzicKFmP89tQFGLGZYy0_34.714646_-86.584970")
        self.failUnlessFailure(d, FakeResponse)
        def after_error(f):
            self.failUnlessEqual(f.code, 500)
            self.assertEqual(mockagent.endpoint, 'http://api.simplegeo.com:80/%s/features/%s.json' % (API_VERSION, "SG_4bgzicKFmP89tQFGLGZYy0_34.714646_-86.584970"))
            self.assertEqual(mockagent.method, 'GET')
        d.addCallback(after_error)
        return d

EXAMPLE_POINT_BODY="""
{"geometry":{"type":"Point","coordinates":[-105.048054,40.005274]},"type":"Feature","id":"SG_6sRJczWZHdzNj4qSeRzpzz_40.005274_-105.048054@1291669259","properties":{"province":"CO","city":"Erie","name":"CMD Colorado Inc","tags":["sandwich"],"country":"US","phone":"+1 303 664 9448","address":"305 Baron Ct","owner":"simplegeo","classifiers":[{"category":"Restaurants","type":"Food & Drink","subcategory":""}],"postcode":"80516"}}
"""

EXAMPLE_BODY="""
{"geometry":{"type":"Polygon","coordinates":[[[-86.3672637,33.4041157],[-86.3676356,33.4039745],[-86.3681259,33.40365],[-86.3685992,33.4034242],[-86.3690556,33.4031137],[-86.3695121,33.4027609],[-86.3700361,33.4024363],[-86.3705601,33.4021258],[-86.3710166,33.4018012],[-86.3715575,33.4014061],[-86.3720647,33.4008557],[-86.3724366,33.4005311],[-86.3730621,33.3998395],[-86.3733156,33.3992891],[-86.3735523,33.3987811],[-86.3737383,33.3983153],[-86.3739073,33.3978355],[-86.374144,33.3971016],[-86.3741609,33.3968758],[-86.3733494,33.3976943],[-86.3729606,33.3980189],[-86.3725211,33.3984141],[-86.3718111,33.3990069],[-86.3713378,33.399402],[-86.370949,33.3997266],[-86.3705094,33.3999948],[-86.3701206,33.4003899],[-86.3697487,33.4007287],[-86.369157,33.4012791],[-86.3687682,33.401646],[-86.3684132,33.4019847],[-86.368092,33.4023798],[-86.3676694,33.4028738],[-86.3674835,33.4033113],[-86.3672975,33.4037487],[-86.3672637,33.4041157],[-86.3672637,33.4041157]]]},"type":"Feature","properties":{"category":"Island","license":"http://creativecommons.org/licenses/by-sa/2.0/","handle":"SG_4b10i9vCyPnKAYiYBLKZN7_33.400800_-86.370802","subcategory":"","name":"Elliott Island","attribution":"(c) OpenStreetMap (http://openstreetmap.org/) and contributors CC-BY-SA (http://creativecommons.org/licenses/by-sa/2.0/)","type":"Physical Feature","abbr":""},"id":"SG_4b10i9vCyPnKAYiYBLKZN7"}
"""

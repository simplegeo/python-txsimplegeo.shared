import unittest
from pyutil import jsonutil as json
from simplegeo.shared import Client, APIError, DecodeError, Feature

from decimal import Decimal as D

import mock

MY_OAUTH_KEY = 'MY_OAUTH_KEY'
MY_OAUTH_SECRET = 'MY_SECRET_KEY'
TESTING_LAYER = 'TESTING_LAYER'

API_VERSION = '1.0'
API_HOST = 'api.simplegeo.com'
API_PORT = 80

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
        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', 'thingie': "just to see if you're listening"}, EXAMPLE_POINT_BODY)
        self.client.http = mockhttp

        res = self.client.get_feature("SG_4bgzicKFmP89tQFGLGZYy0_34.714646_-86.584970")
        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/features/%s.json' % (API_VERSION, "SG_4bgzicKFmP89tQFGLGZYy0_34.714646_-86.584970"))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')
        # the code under test is required to have json-decoded this before handing it back
        self.failUnless(isinstance(res, Feature), (repr(res), type(res)))

        self.failUnless(self.client.get_most_recent_http_headers(), {'status': '200', 'content-type': 'application/json', 'thingie': "just to see if you're listening"})

    def test_get_polygon_feature(self):
        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, EXAMPLE_BODY)
        self.client.http = mockhttp

        res = self.client.get_feature("SG_4bgzicKFmP89tQFGLGZYy0_34.714646_-86.584970")
        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/features/%s.json' % (API_VERSION, "SG_4bgzicKFmP89tQFGLGZYy0_34.714646_-86.584970"))

        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')
        # the code under test is required to have json-decoded this before handing it back
        self.failUnless(isinstance(res, Feature), (repr(res), type(res)))


    def test_type_check_request(self):
        self.failUnlessRaises(TypeError, self.client._request, 'whatever', 'POST', {'bogus': "non string"})

    def test_get_feature_bad_json(self):
        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, EXAMPLE_BODY + 'some crap')
        self.client.http = mockhttp

        try:
            self.client.get_feature("SG_4bgzicKFmP89tQFGLGZYy0_34.714646_-86.584970")
        except DecodeError, e:
            self.failUnlessEqual(e.code,None,repr(e.code))
            self.failUnless("Could not decode JSON" in e.msg, repr(e.msg))
            erepr = repr(e)
            self.failUnless('JSONDecodeError' in erepr, erepr)

        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/features/%s.json' % (API_VERSION, "SG_4bgzicKFmP89tQFGLGZYy0_34.714646_-86.584970"))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')

    def test_dont_json_decode_results(self):
        """ _request() is required to return the exact string that the HTTP
        server sent to it -- no transforming it, such as by json-decoding. """

        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, '{ "Hello": "I am a string. \xe2\x9d\xa4" }'.decode('utf-8'))
        self.client.http = mockhttp
        res = self.client._request("http://thing", 'POST')[1]
        self.failUnlessEqual(res, '{ "Hello": "I am a string. \xe2\x9d\xa4" }'.decode('utf-8'))

    def test_dont_Recordify_results(self):
        """ _request() is required to return the exact string that the HTTP
        server sent to it -- no transforming it, such as by json-decoding and
        then constructing a Record. """

        EXAMPLE_RECORD_JSONSTR=json.dumps({ 'geometry' : { 'type' : 'Point', 'coordinates' : [D('10.0'), D('11.0')] }, 'id' : 'my_id', 'type' : 'Feature', 'properties' : { 'key' : 'value'  , 'type' : 'object' } })

        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '200', 'content-type': 'application/json', }, EXAMPLE_RECORD_JSONSTR)
        self.client.http = mockhttp
        res = self.client._request("http://thing", 'POST')[1]
        self.failUnlessEqual(res, EXAMPLE_RECORD_JSONSTR)

    def test_get_feature_error(self):
        mockhttp = mock.Mock()
        mockhttp.request.return_value = ({'status': '500', 'content-type': 'application/json', }, '{"message": "help my web server is confuzzled"}')
        self.client.http = mockhttp

        try:
            self.client.get_feature("SG_4bgzicKFmP89tQFGLGZYy0_34.714646_-86.584970")
        except APIError, e:
            self.failUnlessEqual(e.code, 500, repr(e.code))
            self.failUnlessEqual(e.msg, '{"message": "help my web server is confuzzled"}', (type(e.msg), repr(e.msg)))

        self.assertEqual(mockhttp.method_calls[0][0], 'request')
        self.assertEqual(mockhttp.method_calls[0][1][0], 'http://api.simplegeo.com:80/%s/features/%s.json' % (API_VERSION, "SG_4bgzicKFmP89tQFGLGZYy0_34.714646_-86.584970"))
        self.assertEqual(mockhttp.method_calls[0][1][1], 'GET')

    def test_APIError(self):
        e = APIError(500, 'whee', {'status': "500"})
        self.failUnlessEqual(e.code, 500)
        self.failUnlessEqual(e.msg, 'whee')
        repr(e)
        str(e)

EXAMPLE_POINT_BODY="""
{"geometry":{"type":"Point","coordinates":[-105.048054,40.005274]},"type":"Feature","id":"SG_6sRJczWZHdzNj4qSeRzpzz_40.005274_-105.048054@1291669259","properties":{"province":"CO","city":"Erie","name":"CMD Colorado Inc","tags":["sandwich"],"country":"US","phone":"+1 303 664 9448","address":"305 Baron Ct","owner":"simplegeo","classifiers":[{"category":"Restaurants","type":"Food & Drink","subcategory":""}],"postcode":"80516"}}
"""

EXAMPLE_BODY="""
{"geometry":{"type":"Polygon","coordinates":[[[-86.3672637,33.4041157],[-86.3676356,33.4039745],[-86.3681259,33.40365],[-86.3685992,33.4034242],[-86.3690556,33.4031137],[-86.3695121,33.4027609],[-86.3700361,33.4024363],[-86.3705601,33.4021258],[-86.3710166,33.4018012],[-86.3715575,33.4014061],[-86.3720647,33.4008557],[-86.3724366,33.4005311],[-86.3730621,33.3998395],[-86.3733156,33.3992891],[-86.3735523,33.3987811],[-86.3737383,33.3983153],[-86.3739073,33.3978355],[-86.374144,33.3971016],[-86.3741609,33.3968758],[-86.3733494,33.3976943],[-86.3729606,33.3980189],[-86.3725211,33.3984141],[-86.3718111,33.3990069],[-86.3713378,33.399402],[-86.370949,33.3997266],[-86.3705094,33.3999948],[-86.3701206,33.4003899],[-86.3697487,33.4007287],[-86.369157,33.4012791],[-86.3687682,33.401646],[-86.3684132,33.4019847],[-86.368092,33.4023798],[-86.3676694,33.4028738],[-86.3674835,33.4033113],[-86.3672975,33.4037487],[-86.3672637,33.4041157],[-86.3672637,33.4041157]]]},"type":"Feature","properties":{"category":"Island","license":"http://creativecommons.org/licenses/by-sa/2.0/","handle":"SG_4b10i9vCyPnKAYiYBLKZN7_33.400800_-86.370802","subcategory":"","name":"Elliott Island","attribution":"(c) OpenStreetMap (http://openstreetmap.org/) and contributors CC-BY-SA (http://creativecommons.org/licenses/by-sa/2.0/)","type":"Physical Feature","abbr":""},"id":"SG_4b10i9vCyPnKAYiYBLKZN7"}
"""

import unittest

from txsimplegeo.shared.oauth import escape, normalize_parameters, signing_base, sign_request, to_unicode

class ReallyEqualMixin:
    def failUnlessReallyEqual(self, a, b, msg=None):
        self.failUnlessEqual(a, b, msg=msg)
        self.failUnlessEqual(type(a), type(b), msg="a :: %r, b :: %r, %r" % (a, b, msg))

class TestFuncs(unittest.TestCase):
   def test_to_unicode(self):
        self.failUnlessRaises(TypeError, to_unicode, '\xae')

        self.failUnlessEqual(to_unicode(':-)'), u':-)')
        self.failUnlessEqual(to_unicode(u'\u00ae'), u'\u00ae')
        self.failUnlessEqual(to_unicode('\xc2\xae'), u'\u00ae')

class OauthTest(unittest.TestCase, ReallyEqualMixin):
    def test_escape(self):
        self.failUnlessReallyEqual(escape('~'), '~')
        self.failUnlessReallyEqual(escape(u'\u2766'), '%E2%9D%A6')

    def test_signing_base(self):
        sb = signing_base('GET', 'http://example.com/api/', {}, 'sekrit')
        self.failUnlessReallyEqual(sb, ('sekrit&', 'GET&http%3A%2F%2Fexample.com%2Fapi%2F&'))

    def test_normalize_parameters(self):
        np = normalize_parameters({'d': 'b', 'c': 'd'})
        self.failUnlessReallyEqual(np, 'c=d&d=b')

        np = normalize_parameters({'a': 'b', 'c': 'd'})
        self.failUnlessReallyEqual(np, 'a=b&c=d')

        np = normalize_parameters({'a': ['e', 'b'], 'c': 'd'})
        self.failUnlessReallyEqual(np, 'a=b&a=e&c=d')

        np = normalize_parameters({'a': 'b c'})
        self.failUnlessReallyEqual(np, 'a=b%20c')

        np = normalize_parameters({'a': 'b~c'})
        self.failUnlessReallyEqual(np, 'a=b~c')

    def test_sign(self):
        authheader = sign_request('abcde', 'fghijk', 'GET', 'http://example.com/api', {}, 'example')
        self.failUnlessReallyEqual(authheader, 'OAuth realm="example", oauth_signature="8b1d544bfc74ae64784dd95b0fffaf2c48a027a4", oauth_consumer_key="abcde", oauth_signature_method="HMAC-SHA1"')

        authheader = sign_request('abcde', 'fghijk', 'GET', 'http://example.com/api', {'a': ['e', 'b'], 'c': 'd'}, 'example')
        self.failUnlessReallyEqual(authheader, 'OAuth realm="example", oauth_signature="769eeb73ed355ad177cf113bc28a85a54c8c8ff6", oauth_signature_method="HMAC-SHA1", oauth_consumer_key="abcde"')

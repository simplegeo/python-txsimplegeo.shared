# copied from https://github.com/simplegeo/python-oauth2 and modified
# to do only what we need here

import hashlib, hmac, urllib

def to_unicode(s):
    """ Convert to unicode, raise exception with instructive error
    message if s is not unicode, ascii, or utf-8. """
    if not isinstance(s, unicode):
        if not isinstance(s, str):
            raise TypeError('You are required to pass either unicode or string here, not: %r (%s)' % (type(s), s))
        try:
            s = s.decode('utf-8')
        except UnicodeDecodeError, le:
            raise TypeError('You are required to pass either a unicode object or a utf-8 string here. You passed a Python string object which contained non-utf-8: %r. The UnicodeDecodeError that resulted from attempting to interpret it as utf-8 was: %s' % (s, le,))
    return s

def escape(s):
    """Escape a URL including any /."""
    return urllib.quote(to_unicode(s).encode('utf-8'), safe='~')

def normalize_parameters(params):
    items = []
    for k, v in params.iteritems():
        # 1.0a/9.1.1 states that kvp must be sorted by key, then by
        # value, so we unpack sequence values into multiple items for
        # sorting.
        if isinstance(v, basestring):
            items.append((k, v))
        else:
            for e in v:
                items.append((k, e))

    # Encode signature parameters per Oauth Core 1.0 protocol spec
    # draft 7, section 3.6
    # (http://tools.ietf.org/html/draft-hammer-oauth-07#section-3.6)
    # Spaces must be encoded with "%20" instead of "+"
    return urllib.urlencode(sorted(items)).replace('+', '%20').replace('%7E', '~')

def signing_base(method, url, params, secret):
    sig = [
        escape(method),
        escape(url),
        escape(normalize_parameters(params)),
    ]

    key = '%s&' % escape(secret)
    raw = '&'.join(sig)
    return key, raw

def sign_request(key, secret, method, url, params, realm):
    params['oauth_consumer_key'] = key
    params['oauth_signature_method'] = 'HMAC-SHA1'

    key, raw = signing_base(method, url, params, secret)

    params['oauth_signature'] = hmac.new(key, raw, hashlib.sha1).hexdigest()

    oauth_params = ((k, escape(to_unicode(v))) for k, v in params.iteritems() if k.startswith('oauth_'))
    header_params = ('%s="%s"' % (k, v) for k, v in oauth_params)
    params_header = ', '.join(header_params)

    auth_header = 'OAuth realm="%s"' % realm
    if params_header:
        auth_header = "%s, %s" % (auth_header, params_header)

    return auth_header

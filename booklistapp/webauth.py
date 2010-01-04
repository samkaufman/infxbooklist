import urllib2
from urllib import urlencode

WEBAUTH_COOKIE_ID = 'ucinetid_auth'

class WebAuthCheck(dict):
    def __init__(self):
        super(WebAuthCheck, self).__init__()
        pass
    def failed(self):
        return 'auth_fail' in self
                
def login():
    '''Logs in with a given UCInetid and
    password, returning the auth code.'''
    pass
    
def check(ucinetid_auth):
    req = urllib2.Request("https://login.uci.edu/ucinetid/webauth_check?" \
                          + urlencode({'ucinetid_auth':ucinetid_auth}))
    conn = urllib2.urlopen(req)
    response = conn.read()
    props = dict([x.split('=') for x in response.split('\n') if len(x) > 0])
    wac = WebAuthCheck()
    for k,v in props.iteritems():
        wac[k] = v
    return wac
    
def logged_in(request, return_id=False):
    '''For Django. Takes the most recent
    HttpRequest. Returns False if not.
    If logged in, will return True, or the UCInetid
    of the logged-in user if given return_id.'''
    from django.http import HttpRequest
    if WEBAUTH_COOKIE_ID in request.COOKIES or WEBAUTH_COOKIE_ID in request.GET:
        c = check(max(HttpRequest.COOKIES[WEBAUTH_COOKIE_ID],HttpRequest.GET[WEBAUTH_COOKIE_ID]))
        if not c.failed():
            if return_id:
                return c.ucinetid
            else:
                return True
    return False
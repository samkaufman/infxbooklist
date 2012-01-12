# -*- coding: utf-8 -*-
# uciwebauth.py

# Copyright (c) 2008-2010, The Regents of the University of California
# Produced by the Laboratory for Fluorescence Dynamics
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
# * Neither the name of the copyright holders nor the names of any
#   contributors may be used to endorse or promote products derived
#   from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""Access UCI WebAuth and LDAP person records. Incl. CGI and Django backends.

:Authors: `Christoph Gohlke <http://www.lfd.uci.edu/~gohlke/>`__

:Version: 2010.04.10

Requirements
------------

*  `Python 2.6 or 3.1 <http://www.python.org>`__
*  `Python-ldap 2.3 <http://python-ldap.sourceforge.net>`__
*  `Django 1.1 <http://www.djangoproject.com/>`__ (optional)

References
----------

(1) NACS WebAuth: A tool for validating UCInetIDs on the Web.
    http://www.nacs.uci.edu/help/webauth
(2) UCI LDAP Directory Service. http://www.nacs.uci.edu/email/ldap.html
(3) User authentication in Django.
    http://www.djangoproject.com/documentation/authentication/

"""

from __future__ import division, print_function

import sys
import os
import re

if sys.version[0] == '2':
    from urllib import urlencode
    from urllib2 import Request, urlopen
    from urlparse import urlunsplit
else:
    from urllib.parse import urlencode, urlunsplit
    from urllib.request import Request, urlopen

import ldap

try:
    from django.conf import settings
    from django.contrib.auth.models import User, check_password
except (ImportError, EnvironmentError):
    pass


class WebAuth(object):
    """Authenticate against UCI WebAuth service.

    Raise WebAuthError if authentication fails.

    Attributes
    ----------

    ucinetid_auth: str or None
        64 character string stored in UCI WebAuth database as key to
        other information about login.

    ucinetid : str or None
        UCInetID authenticated with key.

    auth_host : str or None
        IP number of host that key was authenticated from.

    time_created : int or None
        Seconds since epoch that key was authenticated.

    last_checked : int or None
        Seconds since epoch to when webauth_check was last run on key.

    max_idle_time : int or None

    login_timeout : str or None

    campus_id : int or None
        Unique number for every person on UCI campus that will never be
        duplicated or repeated.

    uci_affiliations : str or None
        List of affiliations that a user has with UCI.
        student | staff | employee | guest | alumni | former_student

    age_in_seconds : int or None
        Number of seconds passed since password was authenticated.

    seconds_since_checked : int or None
        Seconds since last time webauth_check was run on key.

    auth_fail : str or None
        Reason for authorization failure.

    error_code : str or None
        Key to ERROR_CODES.

    Examples
    --------

    >>> try:
    ...     auth = WebAuth(TEST_USER, TEST_PASSWORD)
    ... except WebAuthError as e:
    ...     print(e)
    ... else:
    ...     auth.ucinetid == TEST_USER
    ...     try:
    ...         auth.check()
    ...     except WebAuthError as e:
    ...         print(e)
    ...     try:
    ...         auth.logout()
    ...     except WebAuthError as e:
    ...         print(e)
    True

    >>> auth = WebAuth()
    >>> try:
    ...     auth.authenticate('not a valid ucinetid_auth token')
    ... except WebAuthError as e:
    ...     print(e)
    No valid ucinetid_auth token found

    """

    LOGIN_URL = 'https://login.uci.edu/ucinetid/webauth'
    CHECK_URL = 'https://login.uci.edu/ucinetid/webauth_check'
    LOGOUT_URL = 'https://login.uci.edu/ucinetid/webauth_logout'

    USER_AGENT = {'User-Agent': 'Python-urllib/%s uciwebauth.py' %
                  sys.version.split(' ', 1)[0]}

    ERROR_CODES = {
        'WEBAUTH_DOWN': 'The WebAuth Server is currently down',
        'NO_AUTH_KEY': 'No ucinetid_auth was provided',
        'NOT_FOUND': 'The ucinetid_auth is not in the database',
        'NO_AFFILIATION': 'Access denied to see user information'}

    ATTRS = {'ucinetid': str, 'auth_host': str, 'time_created': int,
        'last_checked': int, 'max_idle_time': int, 'login_timeout': int,
        'campus_id': str, 'uci_affiliations': str, 'age_in_seconds': int,
        'seconds_since_checked': int, 'auth_fail': str, 'error_code': str}

    def __init__(self, usrid=None, password=None):
        if usrid:
            self.authenticate(usrid, password)
        else:
            self._clear()

    def authenticate(self, usrid, password=None):
        """Get ucinetid_auth token.

        Usrid can be a UCInetId, a 64 byte WebAuth token or any string
        containing the token, e.g HTTP QUERY_STRING or HTTP_COOKIE.

        Raise WebAuthError on failure.

        """
        self._clear()
        if password is None and len(usrid) > 8:
            self.ucinetid_auth = self._search_token(usrid)
        else:
            self.ucinetid_auth = self._new_token(usrid, password)
        if not self.ucinetid_auth:
            raise WebAuthError('No valid ucinetid_auth token found')
        self.check()

    def check(self):
        """Get data associated with ucinetid_auth token.

        Raise WebAuthError on failure.

        """
        if not self.ucinetid_auth:
            return
        data = urlencode({'ucinetid_auth': self.ucinetid_auth})
        request = Request(self.CHECK_URL, data, self.USER_AGENT)
        try:
            response = urlopen(request).read()
        except Exception:
            raise WebAuthError("UCI webauth_check site not found")
        for line in response.splitlines():
            try:
                attr, value = line.strip().split("=")
                setattr(self, attr, self.ATTRS[attr](value))
            except (KeyError, ValueError):
                pass
        if self.auth_fail:
            raise WebAuthError(self.auth_fail)

    def logout(self):
        """Clear ucinetid_auth entry in UCI WebAuth database."""
        if not self.ucinetid_auth:
            return
        data = urlencode({'ucinetid_auth': self.ucinetid_auth})
        request = Request(self.LOGOUT_URL, data, self.USER_AGENT)
        try:
            response = urlopen(request).read()
        except Exception:
            raise WebAuthError("UCI webauth_logout site not found")
        self._clear()

    def validate(self, timeout=None, auth_host=None):
        """Raise WebAuthError if no token, timeout, or host mismatch."""
        if not self.ucinetid_auth or len(self.ucinetid_auth) != 64:
            raise WebAuthError("Not logged in")
        if timeout is not None and self.age_in_seconds > timeout:
            raise WebAuthError("Authentication expired")
        if auth_host and self.auth_host != auth_host:
            raise WebAuthError("Host mismatch")

    def login_url(self, return_url=''):
        """Return URL to log in to WebAuth."""
        return self.LOGIN_URL + '?' + urlencode({'return_url': return_url})

    def logout_url(self, return_url=''):
        """Return URL to log out of WebAuth."""
        return self.LOGOUT_URL + '?' + urlencode(
            {'ucinetid_auth': self.ucinetid_auth, 'return_url': return_url})

    def _clear(self):
        """Initialize attributes to None."""
        self.ucinetid_auth = None
        for attr in self.ATTRS.keys():
            setattr(self, attr, None)

    def _search_token(self, search_string):
        """Return ucinetid_auth token from string."""
        if search_string and len(search_string) >= 64:
            pattern = "ucinetid_auth=" if len(search_string) > 64 else ""
            pattern += "([a-zA-Z0-9_]{64})"
            try:
                return re.search(pattern, search_string).group(1)
            except AttributeError:
                pass

    def _new_token(self, ucinetid, password):
        """Authenticate username/password and get new ucinetid_auth token."""
        if password is None or not ucinetid or len(ucinetid) > 8:
            raise WebAuthError("Invalid ucinetid or password")

        data = urlencode({
            'ucinetid': ucinetid, 'password': password,
            'return_url': '', 'referer': '', 'info_text': '',
            'info_url': '', 'submit_type': '', 'login_button': 'Login'})
        request = Request(self.LOGIN_URL, data, self.USER_AGENT)
        try:
            response = urlopen(request)
        except Exception:
            raise WebAuthError("UCI webauth site not found")

        try:
            cookie = response.info()['Set-Cookie']
            if not 'ucinetid_auth' in cookie:
                raise
        except Exception:
            raise WebAuthError("Cookie not found")

        ucinetid_auth = self._search_token(cookie)
        if not ucinetid_auth:
            raise WebAuthError("Authentication failed")

        return ucinetid_auth

    def __str__(self):
        output = ['ucinetid_auth=%s' % self.ucinetid_auth]
        for attr in self.ATTRS.keys():
            value = getattr(self, attr)
            if value is not None:
                output.append("%s=%s" % (attr, value))
        return "\n".join(output)


class WebAuthError(Exception):
    """Base class for errors in the WebAuth class."""
    pass


class LdapPerson(object):
    """A person entry in the UCI LDAP directory.

    Raise LdapPersonError if search fails or results are ambiguous
    or not a person.

    The first item of any LDAP record field listed in ATTRS is stored
    as an attribute.
    The complete LDAP search results are stored as 'records'.

    Examples
    --------

    >>> try:
    ...     p1 = LdapPerson(TEST_USER)
    ... except LdapPersonError:
    ...     print("LdapPerson failed")
    ... else:
    ...     p2 = LdapPerson(p1.campusId)
    ...     p3 = LdapPerson('*%s %s*' % (p1.givenName, p1.sn), 'cn')
    ...     (p1.cn == p2.cn) and (p1.mail == p3.mail)
    True

    """
    SERVER = "ldap.service.uci.edu"
    BASEDN = "ou=University of California Irvine," \
             "o=University of California,c=US"
    TYPES = ('eduPerson', 'PERSON', 'STUDENT')
    ATTRS = ('cn', 'uid', 'campusId', 'ucinetid', 'UCIaffiliation',
             'lastFirstName', 'givenName', 'sn', 'mail', 'telephoneNumber',
             'homePageUrl', 'department', 'postalAddress', 'postalCode',
             'mailcode', 'type', 'AlumniDate', 'AlumniEmail'
             'major', 'studentLevel', 'displayName', 'rewrite',
             'mailDeliveryPoint', 'objectClass', 'pretty_name')

    def __init__(self, value=None, rdn=None, types=TYPES):
        if value:
            self.search(value, rdn, types)
        else:
            self._clear()

    def search(self, value, rdn=None, types=None):
        """Search LDAP directory for value and set attributes from results.

        Value is searched in campusId (if string), ucinetid (if int),
        or relative distinguished name (if specified).

        Raise LdapPersonError on failure.

        """
        self._clear()
        if rdn:
            filter = "%s=%s" % (rdn, value)
        else:
            try:
                filter = "campusId=%.12i" % int(value)
            except Exception:
                filter = "ucinetid=%s" % str(value)

        try:
            l = ldap.open(self.SERVER)
        except ldap.LDAPError as e:
            raise LdapPersonError(e)

        try:
            id = l.search(self.BASEDN, ldap.SCOPE_SUBTREE, filter, None)
            results = []
            while 1:
                type, data = l.result(id, 0)
                if not data:
                    break
                elif type == ldap.RES_SEARCH_ENTRY:
                    results.append(data)
        except ldap.LDAPError as e:
            raise LdapPersonError(e)

        if len(results) != 1:
            raise LdapPersonError("%s not found or result ambiguous." % filter)

        self.DN, self.records = results[0][0]

        if not self._is_type(types):
            raise LdapPersonError("%s has wrong type." % filter)

        for attr in self.ATTRS:
            if attr in self.records:
                value = self.records[attr][0]
                setattr(self, attr, value)

        try:
            self.pretty_name = " ".join((self.givenName.split()[0].title(),
                                         self.sn.title()))
        except Exception:
            self.pretty_name = None

    def _is_type(self, types=TYPES):
        """Return whether record is one of types."""
        if not types:
            return True
        for type in ('objectClass', 'type'):
            if type in self.records:
                for value in self.records[type]:
                    if value in types:
                        return True
        return False

    def _clear(self):
        """Initialize attributes to None."""
        self.records = None
        for attr in self.ATTRS:
            setattr(self, attr, None)

    def __str__(self):
        output = []
        for attr in self.ATTRS:
            output.append("%s=%s" % (attr, getattr(self, attr)))
        return "\n".join(output)


class LdapPersonError(Exception):
    """Base class for errors in the LdapPerson class."""
    pass


class DjangoBackend:
    """Django authentication backend using UCI WebAuth service.

    Add 'path.to.uciwebauth.DjangoBackend' to AUTHENTICATION_BACKENDS
    in the Django project settings.py file.

    """

    def authenticate(self, username=None, password=None):
        try:
            webauth_user = WebAuth(username, password)
        except WebAuthError:
            return None

        if webauth_user.ucinetid:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                # Create a new Django user.
                user = User(username=username, password="")
                user.set_unusable_password()
                try:
                    ldap_user = LdapPerson(webauth_user.campus_id)
                except LdapPersonError:
                    user.email = username + '@uci.edu'
                else:
                    user.first_name = ldap_user.givenName.title()
                    user.last_name = ldap_user.sn.title()
                    user.email = ldap_user.mail
                    if not user.email:
                        user.email = username + '@uci.edu'
                user.is_staff = webauth_user.ucinetid.lower() in [x.lower() for x in settings.ADMIN_UCINETIDS]
                user.is_superuser = user.is_staff
                user.save()
            else:
                should_be_staff = webauth_user.ucinetid.lower() in [x.lower() for x in settings.ADMIN_UCINETIDS]
                if user.is_staff != should_be_staff:
                    # update staff state; write to db
                    user.is_staff = should_be_staff
                    user.is_superuser = should_be_staff
                    user.save()
            return user

        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


class CgiBackend(object):
    """WebAuth backend for use in CGI scripts.

    Attributes
    ----------

    auth : WebAuth

    ldap : LdapPerson or None
        LDAP record of authenticated user.

    username : str
        UCInetId or full name from LDAP of the authenticated user.

    ucinetid : str
        UCInetId of authenticated user.

    messages : list of str
        Messages returned by WebAuth and LdapPerson.

    url : str
        URL of the CGI script.

    """

    def __init__(self, auth_timeout=None, pretty_url=False, env=os.getenv):
        """Initialize CGI backend from environment variables.

        The script file name will be removed from URLs if pretty_url=True.

        """
        self.auth = WebAuth()
        self.ldap = LdapPerson()
        self.url = self._script_url(pretty_url, env)
        self.messages = []
        self.ucinetid = ''
        self.username = ''
        try:
            self.auth.authenticate("%s %s" % (env('QUERY_STRING'),
                                              env('HTTP_COOKIE')))
            self.auth.validate(timeout=auth_timeout,
                               auth_host=env('REMOTE_ADDR'))
        except WebAuthError as e:
            self.messages.append(str(e))
        else:
            self.ucinetid = self.auth.ucinetid
            try:
                self.ldap.search(self.auth.campus_id)
                self.username = self.ldap.pretty_name
            except LdapPersonError as e:
                self.username = self.ucinetid
                self.messages.append(str(e))

    def __str__(self):
        """Return HTML code for logging in to/out of UCI WebAuth system."""
        if self.messages:
            return '<a href="%s" title="Reason: %s">' \
                   'Log in</a> with your UCInetId' % (
                       self.login_url(), self.messages[0])
        else:
            return 'Welcome, <strong>%s</strong> ' \
                   '[ <a href="%s">Log out</a> ]' % (
                self.username, self.logout_url())

    def login_url(self):
        """Return URL for logging in to UCI WebAuth system."""
        return self.auth.login_url(self.url)

    def logout_url(self):
        """Return URL for logging out of UCI WebAuth system."""
        return self.auth.logout_url(self.url)

    def _script_url(self, pretty_url=False, env=os.getenv):
        """Return URL of CGI script, without script file name if pretty_url."""
        netloc = env('SERVER_NAME')
        port = env('SERVER_PORT')
        path = env('SCRIPT_NAME')
        if port and port != '80':
            netloc += ':' + port
        if path is None:
            path = env('PATH_INFO')
        if path is None:
            path = ''
        elif pretty_url:
            s = path.rsplit('/', 1)
            if '.' in s[-1]:
                path = '/'.join(s[:-1])
        scheme = 'https' if (port and int(port) == 443) else 'http'
        return urlunsplit([scheme, netloc, path, '', ''])


def cgi_test(pretty_url=False, out=sys.stdout.write):
    """Print CGI response for testing UCI WebAuth authentication.

    CGI script: ``import uciwebauth; uciwebauth.cgi_test()``

    """
    import cgi
    import cgitb
    cgitb.enable()

    auth = CgiBackend(pretty_url=pretty_url)

    out("Content-type: text/html\n\n")
    out("<html><body>")
    out("<h1>UCI WebAuth Test</h1>")
    out("<p>%s</p>" % auth)

    out("<h2>Error Messages</h2><ul>")
    if auth.messages:
        for msg in auth.messages:
            out("<li>%s</li>" % cgi.escape(msg))
    else:
        out("<li>None</li>")
    out("</ul>")

    out("<h2>WebAuth Record</h2><ul>")
    for item in str(auth.auth).splitlines():
        k, v = item.split('=', 1)
        out("<li>%s: <strong>%s</strong></li>" % (k, cgi.escape(v)))
    out("</ul>")

    out("<h2>LDAP Record</h2><ul>")
    if auth.ldap.cn:
        for item in str(auth.ldap).splitlines():
            k, v = item.split('=', 1)
            out("<li>%s: <strong>%s</strong></li>" % (k, cgi.escape(v)))
    else:
        out("<li>None</li>")
    out("</ul>")

    out("<h2>Environment Variables</h2><ul>")
    for var in (
        'AUTH_TYPE', 'AUTH_PASS', 'CONTENT_LENGTH', 'CONTENT_TYPE', 'DATE_GMT',
        'DATE_LOCAL', 'DOCUMENT_NAME', 'DOCUMENT_ROOT', 'DOCUMENT_URI',
        'GATEWAY_INTERFACE', 'LAST_MODIFIED', 'PATH_INFO',
        'PATH_TRANSLATED', 'QUERY_STRING', 'REMOTE_ADDR', 'REMOTE_HOST',
        'REMOTE_IDENT', 'REMOTE_USER', 'REQUEST_METHOD', 'SCRIPT_NAME',
        'SERVER_NAME', 'SERVER_PORT', 'SERVER_PROTOCOL', 'SERVER_ROOT',
        'SERVER_SOFTWARE', 'HTTP_ACCEPT', 'HTTP_CONNECTION', 'HTTP_HOST',
        'HTTP_PRAGMA', 'HTTP_REFERER', 'HTTP_USER_AGENT', 'HTTP_COOKIE',
        'HTTP_ACCEPT_CHARSET', 'HTTP_ACCEPT_ENCODING', 'HTTP_ACCEPT_LANGUAGE',
        'HTTP_CACHE_CONTROL', 'PATH', ):
        out("<li>%s: <strong>%s</strong></li>" % (
            var, cgi.escape(str(os.getenv(var)))))
    out("</ul>")

    out("<h2>Form Data</h2><ul>")
    form = cgi.FieldStorage()
    if not form:
        out("<li>None</li>")
    else:
        for key in form.keys():
            out("<li>%s: <strong>%s</strong></li>" % (
                cgi.escape(key), cgi.escape(form[key].value)))
        out("</ul>")

    out("</body></html>")


# Documentation in HTML format can be generated with Epydoc
__docformat__ = "restructuredtext en"

if __name__ == "__main__":
    if os.getenv('SERVER_NAME'):
        cgi_test()
    elif len(sys.argv) == 3:
        import doctest
        TEST_USER = sys.argv[1]  # Enter a UCInetId for testing
        TEST_PASSWORD = sys.argv[2]  # Enter a password for testing
        doctest.testmod(verbose=False)
        print(LdapPerson(TEST_USER))
    else:
        import webbrowser
        if sys.version[0] == '2':
            from BaseHTTPServer import HTTPServer
            from CGIHTTPServer import CGIHTTPRequestHandler
            CGIHTTPRequestHandler.cgi_directories = ['']
        else:
            from http.server import HTTPServer, CGIHTTPRequestHandler
            CGIHTTPRequestHandler.cgi_directories = ['/']
        url = "http://localhost:9000/" + os.path.split(sys.argv[0])[-1]
        print("Serving CGI script at", url)
        webbrowser.open(url)
        HTTPServer(('localhost', 9000), CGIHTTPRequestHandler).serve_forever()

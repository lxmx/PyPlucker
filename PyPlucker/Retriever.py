#!/usr/bin/env python

"""
Retriever.py   $Id: Retriever.py,v 1.28 2003/12/17 03:46:01 jimj Exp $

Retrieve data identified by some URL from the appropiate location.


Copyright 1999, 2000 by Holger Duerer <holly@starship.python.net>

Distributable under the GNU General Public License Version 2 or newer.
"""

import os, sys
import string
import re
import urllib.request, urllib.parse, urllib.error
import types

## The following section tries to get the PyPlucker directory onto the
## system path if called as a script and if it is not yet there:
try: import PyPlucker
except ImportError:
    file = sys.argv[0]
    while os.path.islink (file): file = os.readlink (file)
    sys.path = [os.path.split (os.path.dirname (file))[0]] + sys.path
    try: import PyPlucker
    except ImportError:
        print("Cannot find where module PyPlucker is located!")
        sys.exit (1)

    # and forget the temp names...
    del file
del PyPlucker
##
## Now PyPlucker things should generally be importable
##

try:
    import gzip
    import io
    _have_gzip = 1
except:
    _have_gzip = 0

from PyPlucker import Url, __version__
from .UtilFns import error, message

def GuessType (name):
    """Given a name, guess the mime type"""
    name = name.lower()
    def has_extension (ext, name=name):
        return name[-len(ext):] == ext

    known_map = { '.gif': 'image/gif',
                  '.png': 'image/png',
                  '.jpg': 'image/jpeg',
                  '.jpe': 'image/jpeg',
                  '.jpeg': 'image/jpeg',
                  # FIXME: Bugs with webp when using bpp=16
                  '.webp': 'image/webp',
                  '.html': 'text/html',
                  '.htm': 'text/html',
                  '.txt': 'text/plain',
                  '.asc': 'text/plain',
                  }
    for ext in list(known_map.keys ()):
        if has_extension (ext):
            return known_map[ext]
    return 'unknown/unknown'


class PluckerFancyOpener (urllib.request.FancyURLopener):
    """A subclass of urllib.FancyURLopener, so we can remember an
    error code and the error text."""

    def __init__(self, alias_list=None, config=None, *args):
        urllib.request.FancyURLopener.__init__(*(self,) + args)
        self._alias_list = alias_list
        self.remove_header ('User-Agent')
        user_agent = (config and config.get_string('user_agent', None)) or 'Plucker/Py-%s' % __version__
        self.addheader ('User-Agent', user_agent)
        referrer = config and config.get_string('referrer', None)
        if referrer:
            self.addheader('Referer', referrer)
        self.addheader ('Accept', 'image/jpeg, image/gif, image/png, image/webp, text/html, text/plain, text/xhtml;q=0.8, text/xml;q=0.6, text/*;q=0.4')

        if 'HTTP_PROXY' in os.environ and ('HTTP_PROXY_USER' in os.environ and 'HTTP_PROXY_PASS' in os.environ):
            import base64
            auth_header = os.environ['HTTP_PROXY_USER'] + ":" + os.environ['HTTP_PROXY_PASS']
            encoded_header = base64.b64encode(bytes(auth_header, 'ascii'))
            self.addheader ('Proxy-Authorization', 'Basic %s' % encoded_header.decode('ascii').strip())
        #for header in self.addheaders: message(0, "%s", header)


    def remove_header (self, header):
        """Remove the header information 'header' if on the header list.
           Return if found on list.
        """
        for i in range (len (self.addheaders)):
            if self.addheaders[i][0] == header:
                del self.addheaders[i]
                return 1
        return 0


def parse_http_header_value(headerval):
    mval = None
    parameters = []
    parts = headerval.split (";")
    if parts:
        mval = parts[0].lower()
    for part0 in parts[1:]:
        part = part0.lower().strip()
        m = re.match ('([-a-z0-9]+)=(.*)', part)
        if m:
            parameters.append(m.groups())
    return mval, parameters


class SimpleRetriever:
    """A very simple retriver.  Not much of error checking, no
    persistent caching.  Just a wrapper around urllib."""

    def __init__ (self, pluckerdir, pluckerhome, configuration=None):
        self._plucker_dir = os.path.expanduser( os.path.expandvars (pluckerdir))
        self._plucker_home = os.path.expanduser( os.path.expandvars (pluckerhome))
        self._cache = {}
        self._configuration = configuration
        # without this, windows and no proxy was very slow
        self._urlopener = PluckerFancyOpener (config=self._configuration)

    def _retrieve_plucker (self, url, alias_list):
        path = url.get_path ()
        if path[0] != '/':
            raise RuntimeError("plucker: URL must give absolute path! (%s)" % path)
        filename1 = os.path.join (self._plucker_dir, path[1:])
        filename2 = os.path.join (self._plucker_home, path[1:])
        if os.path.exists (filename1):
            filename = filename1
        elif os.path.exists (filename2):
            filename = filename2
        else:
            return ({'URL': url,
                     'error code': 404,
                     'error text': "File not found"},
                    None)
        try:
            file = open (filename, "rb")
            contents = file.read ()
            file.close ()
        except IOError as text:
            return ({'URL': url,
                     'error code': 404,
                     'error text': text},
                    None)
        return ({'URL': url,
                 'error code': 0,
                 'error text': "OK",
                 'content-type': GuessType (filename),
                 'content-length': len (contents)},
                contents)

    def _retrieve (self, url, alias_list, post_data):
        """Really retrieve the url."""
        if url.get_protocol () == 'plucker':
            return self._retrieve_plucker (url, alias_list)

        elif url.get_protocol () == 'mailto':
            # Nothing to fetch really...
            return ({'URL': url,
                     'error code': 0,
                     'error text': "OK",
                     'Content-Type': "mailto/text",
                     'content-length': 0},
                     "")

        else:
            # not a plucker:... URL
            try:
                real_url = str (url)
                webdoc = self._urlopener.open (real_url, post_data)
                if webdoc.status and (400 <= webdoc.status < 600):
                    headers_dict = {'URL': real_url,
                                    'error code': webdoc.status,
                                    'error text': 'HTTP error ' + str(webdoc.status)}
                    headers_dict.update (dict(webdoc.info()))
                    return (headers_dict, None)
                if hasattr (webdoc, 'url'):
                    (webdoc_protocol, webdoc_rest_of_url) = urllib.parse.splittype(webdoc.url)

                    # check to see we have a valid URL; if not, use one we started with
                    if webdoc_protocol:
                        real_url = webdoc.url

                headers_dict = {'URL': real_url}
                doc_info = webdoc.info ()
                message(3, "doc_info is %s", doc_info);
                if doc_info is not None:
                    headers_dict.update (dict(doc_info))
                if ('Content-Type' not in headers_dict) and ('content-type' not in headers_dict):
                    message (1, "Guessing type for %s" % url.get_path ())
                    headers_dict['Content-Type'] = GuessType (url.get_path ())
                else:
                    for h in ['Content-Type', 'content-type']:
                        if h in headers_dict:
                            hname = h
                    ctype, parameters = parse_http_header_value(headers_dict[hname])
                    headers_dict['Content-Type'] = ctype
                    for parm in parameters:
                        headers_dict[parm[0]] = parm[1]

                message(3, "headers_dict is %s", headers_dict);

                # Now get the contents
                contents = webdoc.read ()

                # Check if encoded contents...
                if 'content-encoding' in headers_dict:
                    encoding = headers_dict['content-encoding']
                    if encoding == 'gzip' and _have_gzip:
                        s = io.StringIO (contents)
                        g = gzip.GzipFile (fileobj=s)
                        c = g.read ()
                        g.close ()
                        contents = c
                    else:
                        return ({'URL': real_url,
                                 'error code': 404,
                                 'error text': "Unhandled content-encoding '%s'" % encoding},
                                None)

            except IOError as text:
                return ({'URL': real_url,
                         'error code': 404,
                         'error text': text},
                        None)
            except OSError as text:
                return ({'URL': real_url,
                         'error code': 404,
                         'error text': text},
                        None)
            headers_dict['error code'] = 0
            headers_dict['error text'] = "OK"
            return (headers_dict,
                    contents)


    def retrieve (self, url, alias_list, post_data):
        """Fetch some data.
        Return a tuple (headers_dict, data)"""

        if not isinstance (url, Url.URL):
            url = str (url) # convert to string, if not yet so
            url = Url.URL (Url.CleanURL (url))

        data_key = (str (url), post_data)
        if data_key in self._cache:
            # has been retrieved before, we just return the cached data
            return self._cache[data_key]
        else:
            result = self._retrieve (url, alias_list, post_data)
            self._cache[data_key] = result
            newurl = getattr(result, 'URL', url).as_string(with_fragment=None)
            alias_list.add(url,newurl)
            return result




if __name__ == '__main__':
    # called as a script
    import sys
    retriever = SimpleRetriever ("~/.plucker", "~/.plucker")
    for name in sys.argv[1:]:
        print("\n\nFetching %s" % name)
        (header, data) = retriever.retrieve (name, None, None)
        items = list(header.keys ())
        items.sort ()
        print("Headers:")
        for item in items:
            print("  %s:\t%s" % (item, header[item]))
        print("Data:")
        text = repr (data)[1:-1]
        if len (text) > 80:
            text = text[:60] + " ... " + text[-10:]
        print("  " + text)


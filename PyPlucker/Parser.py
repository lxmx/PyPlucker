#!/usr/bin/env python

"""
Parser.py   $Id: Parser.py,v 1.22 2005/01/12 01:47:16 chrish Exp $


Copyright 1999,2000 by Holger Duerer <holly@starship.python.net>

Distributable under the GNU General Public License Version 2 or newer.
"""

from PyPlucker import TextParser, ImageParser, PluckerDocs, ConversionParser
from PyPlucker.ConversionParser import WordParser
from .UtilFns import message, error

unknown_things = {}


def generic_parser (url, headers, data, config, attributes):
    try:
        url = str (url) # convert to string if this is still a Url.ULR
        type = headers['Content-Type']
        verbosity = config.get_int('verbosity', 1)
        if type == 'unknown/unknown' and 'type' in attributes:
            # note that this type is not an HTTP header, and may not contain parameters
            type = attributes['type']
        if type == "text/html":
            parser = TextParser.StructuredHTMLParser (url, data, headers, config, attributes)
            for item in parser.get_unknown ():
                if item in unknown_things:
                    unknown_things[item].append (url)
                else:
                    unknown_things[item] = [url]
            return parser.get_plucker_doc ()
        # DRS 2004-12-29
        # pretend message/rfc822 is really text
        elif type == "text/plain" or type == "message/rfc822":
            parser = TextParser.PlainTextParser (url, data, headers, config, attributes)
            return parser.get_plucker_doc ()
        elif type == "mailto/text":
            # These are easy to handle, the document does it itself, so no
            # parsing needed as we generate the document directly
            return PluckerDocs.PluckerMailtoDocument (url)
        elif type[:6] == "image/":
            # this can fail, as some parsers do not recognize all image types...
            parser = ImageParser.get_default_parser(config)
            parsed = parser (url, type, data, config, attributes)
            return parsed.get_plucker_doc ()
        elif type[:18] == "application/msword":
            return WordParser (url, data, headers, config, attributes)
        else:
            message(0, "%s type not yet handled (%s)" % (type, url))
            return None
    except RuntimeError as text:
        error("Runtime error parsing document %s: %s" % (url, text))
        return None
    except AssertionError as text:
        error("Assertion error parsing document %s: %s" % (url, text))
        return None
    except:
        import traceback
        error("Unknown error parsing document %s:" % url)
        traceback.print_exc ()
        return None

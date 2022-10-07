__version__ = "3.7"

lib_dir = "/usr/local/etc"

DEFAULT_IMAGE_PARSER_SETTING = "pillow"

import sys
if sys.platform == 'win32':
    _SYS_CONFIGFILE_NAME = "plucker.ini"
    _USER_CONFIGFILE_NAME = "plucker.ini"
else:
    _SYS_CONFIGFILE_NAME = "pluckerrc"
    _USER_CONFIGFILE_NAME = ".pluckerrc"


# try to figure out default character set, if any, by using the POSIX locale
DEFAULT_LOCALE_CHARSET_ENCODING = None
try:
    import locale
    locale.setlocale(locale.LC_ALL,"")
    DEFAULT_LOCALE_CHARSET_ENCODING = locale.getlocale()[1]
    ###################################################################
    # locale.getlocale()[1] return an Number (for example 1252)       #
    # on Windows and charset_name_to_mibenum think thats the mibenum  #
    # so we need create an full charset name                          #
    ###################################################################
    if sys.platform == 'win32':
        import re
        if re.match('^[0-9]+$', DEFAULT_LOCALE_CHARSET_ENCODING):
            DEFAULT_LOCALE_CHARSET_ENCODING = "windows-%s" % DEFAULT_LOCALE_CHARSET_ENCODING
except:
    pass



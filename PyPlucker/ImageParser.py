#!/usr/bin/env python2
#  -*- mode: python; indent-tabs-mode: nil; -*-

"""
ImageParser.py   $Id: ImageParser.py,v 1.63 2008/01/21 17:23:21 prussar Exp $

This defines various classes to parse an image to a PluckerImageDocument.

It will try to identify the best available solution to do so and
define that as a default_parser function.


Some parts Copyright 1999 by Ondrej Palkovsky <ondrap@penguin.cz> and
others Copyright 1999 by Holger Duerer <holly@starship.python.net>

Distributable under the GNU General Public License Version 2 or newer.
"""

import os, sys, string, tempfile, re, operator
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
from PyPlucker import PluckerDocs, DEFAULT_IMAGE_PARSER_SETTING
from PyPlucker.UtilFns import message, error


binary_flag = ""
if sys.platform == 'os2':
    binary_flag = 'b'

# This is the maximum size for a simple stored image.
SimpleImageMaxSize = (60 * 1024)


# Match pattern for information in a PNM header file
pnmheader_pattern = re.compile(r"(P[1,4]\n([0-9]+)\s([0-9]+)\n)|(P[2,3,5,6]\n([0-9]+)\s([0-9]+)\n([0-9]+)\n)", re.DOTALL)
geometry_pattern = re.compile(r"([0-9]+)x([0-9]+)\+([0-9]+)\+([0-9]+)")


# Match pattern for information in a MIFF header file
miffrows_pattern = re.compile("\srows=(?P<rows>[0-9]+)\s", re.MULTILINE)
miffcols_pattern = re.compile("\scolumns=(?P<columns>[0-9]+)\s", re.MULTILINE)


#Match pattern for convert version
version_pattern = re.compile("\s([0-9]+).([0-9]+).([0-9]+)[+\s]")


# simple test for checking to see whether a string contains an int
int_pattern = re.compile(r'(^[0-9]+$)|(^0x[0-9a-fA-F]+$)')
def is_int (s):
    return int_pattern.match(s)


#####################################################################
##
## Some standard exceptions used by ImageParser classes.
##

class UnimplementedMethod(AttributeError):
    def __init__(self, value):
        AttributeError.__init__(self, value)

class ImageSize(ValueError):
    def __init__(self, value):
        ValueError.__init__(self, value)

#####################################################################
##
## A general class to handle image parsing.  Actual functionality
## is provided by a subclass which manipulates images via some
## image-processing toolkit.
##

class ImageParser:
    """Provides functions needed to properly convert an image to the Plucker image format.
    Actual functionality is provided by subclasses which manipulate images via some
    image-processing toolkit."""

    # an ordered list of known bit depths
    _known_depths = [1, 2, 4, 8, 16]

    def __init__(self, url, type, bits, config, attributes):
        # sys.stderr.write("attributes are " + str(attributes) + "\n")
        self._url = str(url)
        self._type = type
        self._bits = bits
        self._config = config
        self._attribs = attributes
        self._verbose = config.get_int ('verbosity', 1)
        self._auto_scale = config.get_bool('auto_scale_images', 0) or config.get_bool('try_reduce_dimension', 0) or config.get_bool('try_reduce_bpp', 0)

    def size(self):

        "Returns width and height of original image, as integers, in pixels"

        raise UnimplementedMethod("method 'size' not implemented in class " + str(self.__class__))

    def convert(self, width, height, depth, section=None, prescale=None):

        """Takes width, height, and depth, and returns the bits of a Plucker
        format image having that width, height, and depth.  If section is
        defined, it should be a tuple containing 4 elements:
        (upper-left x, upper-left y, width, height), and means that only
        that section of the original image will be converted.
        If prescale is defined, it should be a tuple containing 2 elements:
        (width, height) and means that image should be scaled to this size
        before cropping. Used for building multi-image documents."""

        raise UnimplementedMethod("method 'convert' not implemented in class " + str(self.__class__))


    def calculate_desired_size(self):

        """Returns a tuple of (DESIRED_SIZE, LIMITS, and SCALING_FACTOR),
        where DESIRED_SIZE is a 4-ple of WIDTH (pixels), HEIGHT (pixels),
        BPP, and SECTION, where section is a 4-ple of (ULX, ULY, WIDTH, HEIGHT),
        indicating a subarea of the whole original image that should be
        converted.  SECTION may be None if the whole images is to be taken.
        LIMITS is a 2-ple containing the values for maxwidth and maxheight
        actually used, and SCALING_FACTOR is a number (float or int)
        the original image size was scaled by.
        It should normally never be necessary to override this method."""

        geometry = self._attribs.get('section')
        section = None
        if geometry:
            m = geometry_pattern.match(geometry)
            if m:
                section = (int(m.group(3)), int(m.group(4)), int(m.group(1)), int(m.group(2)))
        bpp = int(self._attribs.get('bpp') or self._config.get_int('bpp', 1))
        maxwidth = int(self._attribs.get('maxwidth') or self._config.get_int ('maxwidth', 0))
        maxheight = int(self._attribs.get('maxheight') or self._config.get_int ('maxheight', 0))
        width = 0
        height = 0

        # First, look for an explicit width and/or height
        w = self._attribs.get('width')
        h = self._attribs.get('height')
        if w and w[-1] != '%':
            width = int(w)
            scaling_factor = 0
        if h and h[-1] != '%':
            height = int(h)
            scaling_factor = 0

        # Next, check for a geometry cut, and use that if present
        if not width and section and section[2]:
            width = section[2]
        if not height and section and section[3]:
            height = section[3]

        # finally, use the current size of the image
        size = self.size()
        if not width:
            if height and size[1]:
                width = size[0] * height / size[1]
            else:
                width = size[0]
        if not height:
            if width and size[0]:
                height = size[1] * width / size[0]
            else:
                height = size[1]

        # now scale to fit in maxwidth/maxheight
        scaling_factor = 1
        if (maxwidth and width>maxwidth) or (maxheight and height>maxheight):
            if (not maxheight or (maxwidth and float(width)/maxwidth > float(height)/maxheight)):
                scaling_factor = float(maxwidth)/float(width)
            else:
                scaling_factor = float(maxheight)/float(height)

        width = int(width * scaling_factor)
        height = int(height * scaling_factor)
        size = (width, height, bpp, section)
        message(2, "desired_size of image is %s with maxwidth=%d, maxheight=%d" % (size, maxwidth, maxheight))
        return (size, (maxwidth, maxheight), scaling_factor)


    def _related_images (self, scaled):

        """For in-line images, we sometimes provide an alternate version of the image
        which uses the "alt_maxwidth" and "alt_maxheight" parameters, and which is linked
        to the the smaller version.  There may be other reasons to add alternate versions
        of an image, too.  This method generates a list of (URL, ATTRIBUTES) pairs, each
        describing a desired alternate version of the current image, and returns them."""

        new_sizes = []

        if self._attribs.get('_plucker_from_image') and scaled:
            # this is an in-line image.  Let's create the right attributes for a larger
            # version.
            if self._config.get_string('alt_maxwidth') or self._config.get_string('alt_maxheight'):
                # We can turn off alt images by maxing either one or the other to a string of "-1".
                if self._config.get_string('alt_maxwidth') != "-1" and self._config.get_string('alt_maxheight') != "-1":
                    new_attributes = self._attribs.copy()
                    del new_attributes['_plucker_from_image']
                    new_attributes['_plucker_alternate_image'] = 1
                    if self._config.get_string('alt_maxwidth', None):
                        new_attributes['maxwidth'] = self._config.get_string('alt_maxwidth', None)
                    if self._config.get_string('alt_maxheight', None):
                        new_attributes['maxheight'] = self._config.get_string('alt_maxheight', None)
                    new_sizes.append((self._url, new_attributes))

        return new_sizes


    def get_plucker_doc(self):

        """Returns the PluckerDocs.PluckerImageDocument associated with this image, converting
        the original image along the way, if necessary.  It should normally never be necessary
        to override this method."""

        (width, height, depth, section), limits, scaling_factor = self.calculate_desired_size()
        message(2, "Converting image %s with %s" % (self._url, str(self.__class__)))
        newbits = self.convert(width, height, depth, section)

        if len(newbits) > SimpleImageMaxSize and self._auto_scale:

            if self._config.get_bool('try_reduce_bpp', 0) and depth in self._known_depths:
                # try to reduce the depth while keeping the size
                i = self._known_depths.index(depth)
                while (i > 0) and (len(newbits) > SimpleImageMaxSize):
                    i = i - 1
                    olddepth = depth
                    depth = self._known_depths[i]
                    message(2, "Plucker version of image at %dx%dx%d was"
                            " %.0f%% too large, trying depth of %d...\n",
                            width, height, olddepth,
                            (float(len(newbits)-SimpleImageMaxSize)/
                             float(SimpleImageMaxSize)) * 100.0, depth)
                    newbits = self.convert(width, height, depth, section)

            elif (self._config.get_bool('try_reduce_dimension', 0) or
                  self._config.get_bool('auto_scale_images')):
                # try to reduce the image size to fit in a Plucker record
                import math
                target_size = SimpleImageMaxSize
                while len(newbits) > SimpleImageMaxSize:
                    old_target_size = target_size
                    target_size = 0.95 * target_size
                    scaling_factor = math.sqrt(float(target_size)/float(len(newbits)))
                    message(2, "Plucker version of image at %dx%d was "
                            "%.0f%% too large, trying %dx%d...\n",
                            width, height,
                            (float(len(newbits)-old_target_size)/float(old_target_size)) * 100.0,
                            int(scaling_factor * width),
                            int(scaling_factor * height))
                    width = int(scaling_factor * width)
                    height = int(scaling_factor * height)
                    newbits = self.convert(width, height, depth, section)
            else:
                message(2, "You aren't using a try_reduce_depth=1 nor a "
                        "try_reduce_dimension=1. Will proceed to multiimage..")

        if len(newbits) == 0:
            # Oops, nothing fetched?!?
            raise ImageSize("Converted image size for %s is zero bytes. Nothing fetched?" % self._url)

        elif len(newbits) > SimpleImageMaxSize:
            # image bits too large for a _SINGLE_ Plucker image record
            return self.write_multiimage(width, height, depth)

        newurl = "%s?width=%d&height=%d&depth=%d" % (self._url, width, height, depth)
        if section:
            newurl = newurl + "&section=%dx%d+%d+%d" % section
        doc = PluckerDocs.PluckerImageDocument (newurl, self._config)
#       doc = PluckerDocs.PluckerImageDocument (self._url, self._config)
        doc.set_data(newbits)
        # check for alternative versions of this image
        # First, figure out if the image has been scaled down at all
        full_width, full_height = self.size()
        attrib_width = self._attribs.has_key('width') and is_int(self._attribs.get('width')) and int(self._attribs.get('width'))
        attrib_height = self._attribs.has_key('height') and is_int(self._attribs.get('height')) and int(self._attribs.get('height'))
        versions = self._related_images(width < (attrib_width or (section and section[2]) or full_width) or
                                        height < (attrib_height or (section and section[3]) or full_height))
        map(lambda x, doc=doc: doc.add_related_image(x[0], x[1]), versions)
        return doc


    def write_multiimage(self, width, height, depth):
        """Write a multi image record!"""

        if depth == 1:
            wide = 800
            high = 600
        elif depth == 2:
            wide = 600
            high = 400
        elif depth == 4:
            wide = 400
            high = 300
        elif depth == 8:
            wide = 300
            high = 200
        else:
            wide = 300
            high = 100

        cols = width / wide
        if width % wide:
            cols = cols + 1

        rows = height / high
        if height % high:
            rows = rows + 1

        multiurl = "%s?width=%d&height=%d&depth=%d" % (self._url, width, height, depth)
        doc = PluckerDocs.PluckerMultiImageDocument (multiurl, self._config)
        doc.set_size(cols, rows)

        count = 0
        Y = 0
        X = 0

        while Y < height:
            while X < width:
                W = min(wide, width - X)
                H = min(high, height - Y)

                piece_url = "%sMulti%d?width=%d&height=%d&depth=%d" % (self._url, count, width, height, depth)
                piece_doc = PluckerDocs.PluckerImageDocument (piece_url, self._config)
                bits = self.convert(W, H, depth, (X, Y, W, H), (width, height))
                piece_doc.set_data(bits)
                id = PluckerDocs.obtain_fresh_id()
                doc.add_piece_image(piece_doc, id)
                count = count + 1
                X = X + wide
            X = 0
            Y = Y + high

        # check for alternative versions of this image
        # First, figure out if the image has been scaled down at all
        full_width, full_height = self.size()
        versions = self._related_images(width < full_width or height < full_height)
        map(lambda x, doc=doc: doc.add_related_image(x[0], x[1]), versions)
        return doc



#####################################################################
##
## This is an updated version of the standard parser from Ondrej.  It depends on os.popen
## and the availability of the pbmtools plus the updated Tbmp-tools that can handle color.
##

class NewNetPBMImageParser(ImageParser):
    "Convert an image to the PalmBitmap. Uses netpbm."

    def __init__(self, url, type, data, config, attribs, compress=1):
        ImageParser.__init__(self, url, type, data, config, attribs)
        self._size = None
        self._pnmdata = None
        self._tmpfile = tempfile.mktemp()
        try:
            self._convert_to_pnm()
        except:
            if self._verbose > 1:
                import traceback
                traceback.print_exc()
            raise RuntimeError("Error while opening image " + self._url + " with netpbm")


    def _convert_to_pnm(self):

        giftopnm = self._config.get_string ('giftopnm_program', 'giftopnm')
        djpeg = self._config.get_string ('djpeg_program', 'djpeg')
        pngtopnm = self._config.get_string ('pngtopnm_program', 'pngtopnm')
        palmtopnm = self._config.get_string ('palmtopnm_program', 'palmtopnm')
        if (self._type=='image/gif'):
            command = giftopnm
        elif (self._type=='image/jpeg'):
            command = djpeg + ' -pnm'
        elif (self._type=='image/png'):
            command = pngtopnm
        elif (self._type=='image/palm'):
            command = palmtopnm
        elif (self._type=='image/pbm') or (self._type == 'image/x-portable-pixmap') or (self._type == 'image/x-portable-anymap'):
            command = None
        else:
            raise ValueError("unsupported image type " + self._type + " encountered")

        # so convert to PNM bits by running the appropriate command
        if command == None:
            # already in PNM format, skip conversion
            self._pnmdata = self._bits
        else:
            try:
                command = command + " > " + self._tmpfile
                if self._verbose > 1:
                    message(2, "Running:  " + command)
                else:
                    command = "( " + command + " ) 2>/dev/null"
                pipe = os.popen(command, "w"+binary_flag)
                pipe.write(self._bits)
                status = pipe.close()
                if status:
                    raise RuntimeError("call to '" + command + "' returned status " + str(status))
                f = open(self._tmpfile, 'r'+binary_flag)
                self._pnmdata = f.read()
                f.close()
            finally:
                if os.path.exists(self._tmpfile): os.unlink(self._tmpfile)

        # now read the width and height from the PNM data
        m = pnmheader_pattern.match(self._pnmdata)
        if not m:
            raise RuntimeError("Invalid PNM header found in converted PNM data:  %s" % str(self._pnmdata[:min(len(self._pnmdata),15)]))
        if m.group(1):
            # monochrome, so no depth element
            self._size = (int(m.group(2)), int(m.group(3)))
        else:
            # greyscale or color, so use second group
            self._size = (int(m.group(5)), int(m.group(6)))


    def size (self):
        return self._size


    def convert (self, width, height, bpp, section, prescale=None):

        pnmscale = self._config.get_string ('pnmscale_program', 'pnmscale')
        pnmcut = self._config.get_string ('pnmcut_program', 'pnmcut')
        ppmquant = self._config.get_string ('ppmquant_program', 'ppmquant')
        ppmtoTbmp = self._config.get_string ('ppmtoTbmp_program', 'pnmtopalm')
        ppmtopgm = self._config.get_string ('ppmtopgm_program', 'ppmtopgm')
        pgmtopbm = self._config.get_string ('pgmtopbm_program', 'pgmtopbm')
        palm1gray = self._config.get_string ('palm1bit_graymap_file', '/usr/share/netpbm/palmgray1.map')
        palm2gray = self._config.get_string ('palm2bit_graymap_file', '/usr/share/netpbm/palmgray2.map')
        palm4gray = self._config.get_string ('palm4bit_graymap_file', '/usr/share/netpbm/palmgray4.map')
        palm8color = self._config.get_string ('palm8bit_stdcolormap_file', '/usr/share/netpbm/palmcolor8.map')

        if prescale:
            prescale_cmd = pnmscale + " -width %d -height %d | " % (prescale)
        else:
            prescale_cmd = None

        if section:
            pnmcut_cmd = pnmcut + (" %d %d %d %d |" % section)
            size = (section[2], section[3])
        else:
            pnmcut_cmd = ""
            size = self._size

        if width != size[0] or size[1] != height:
            message(2, "Scaling original %dx%d image by %f,%f to %dx%dx%d" % (size[0], size[1], float(width)/float(size[0]), float(height)/float(size[1]), width, height, bpp))

        if (size[0] != width or size[1] != height):
            scale_cmd = pnmscale + " -width %d -height %d " % (width, height)
        else:
            scale_cmd = None

        if bpp == 1:
            ppmquant = ppmtopgm
            ppmquant2 = " | " + pgmtopbm + " -fs "
            ppmtoTbmp = ppmtoTbmp + " -depth 1"
        elif bpp == 2:
            ppmquant2 = " -map " + palm2gray + "|" + ppmtopgm
            ppmtoTbmp = ppmtoTbmp + " -depth 2"
        elif bpp == 4:
            ppmquant2 = " -map " + palm4gray + "|" + ppmtopgm
            ppmtoTbmp = ppmtoTbmp + " -depth 4"
        elif bpp == 8:
            ppmquant2 = " -map " + palm8color + " "
            ppmtoTbmp = ppmtoTbmp + " -depth 8"
        elif bpp == 16:        # direct color
            ppmquant = "cat"
            ppmquant2 = ""
            ppmtoTbmp = ppmtoTbmp + " -depth 16"
        else:
            raise RuntimeError("Can't handle bpp value of %d" % bpp)

        if self._verbose > 1:
            ppmtoTbmp = ppmtoTbmp + " -verbose "
        else:
            ppmtoTbmp = ppmtoTbmp + " -quiet "
            if ppmquant != "cat":
                ppmquant = ppmquant + " -quiet "

        if not scale_cmd:
            command = ppmquant + ppmquant2 + " | " + ppmtoTbmp
        else:
            command = scale_cmd + " | " + ppmquant + ppmquant2 + " | " + ppmtoTbmp
        if pnmcut_cmd:
            command = pnmcut_cmd + command
        if prescale_cmd:
            command = prescale_cmd + command

        command = command + " > " + self._tmpfile
        if self._verbose > 1:
            message(2, "Running:  " + command)
        else:
            command = "( " + command + " ) 2>/dev/null"
        try:
            pipe = os.popen(command, 'w'+binary_flag)
            pipe.write(self._pnmdata)
            status = pipe.close()
            if status:
                raise RuntimeError("call to '" + command + "' returned status " + str(status))
            f = open(self._tmpfile, 'r'+binary_flag)
            newbits = f.read()
            f.close()
            return newbits
        finally:
            if os.path.exists(self._tmpfile): os.unlink(self._tmpfile)


#####################################################################
##
## This is a parser for Windows systems.  It relies on a
## and the availability of the ImageMagic plus the Tbmp tools
##
## FIXME: 100% sure it's broken
##
class WindowsImageParser:
    """Do it on Windows.  Ask Dirk Heiser <plucker@dirk-heiser.de> if
    these tools goof up.  I cannot test it."""
    def __del__ (self):
        self.DeleteTempFiles(self._temp_files)



    def __init__ (self, url, type, data, config, attribs, compress=1):
        # The Result
        self._doc = None
        self._scaled = 0

        #Init some variables
        self._config = config
        self._max_tbmp_size = config.get_int ('max_tbmp_size', SimpleImageMaxSize)
        self._guess_tbmp_size = config.get_bool ('guess_tbmp_size', 1)
        self._try_reduce_bpp = config.get_bool ('try_reduce_bpp', 1)
        self._try_reduce_dimension = config.get_bool ('try_reduce_dimension', 1)
        self._bpp = attribs.get('bpp')
        self._type = type
        self._verbose = config.get_int ('verbosity', 1)
        self._imagemagick = "%s %s" % (self.quotestr(config.get_string ('convert_program','convert.exe')),config.get_string ('convert_program_parameter','%input% bmp:%output%'))
        self._bmp2tbmp = "%s %s" % (self.quotestr(config.get_string ('bmp_to_tbmp', 'Bmp2Tbmp.exe')),config.get_string ('bmp_to_tbmp_parameter','-i=%input% -o=%output% -maxwidth=%maxwidth% -maxheight=%maxheight% -compress=%compress% -bpp=%colors%'))
        if compress:
            self._compress = self._config.get_bool('tbmp_compression', 0)
        else:
            self._compress = 0
        maxwidth = attribs.get('maxwidth')
        maxheight = attribs.get('maxheight')
        if maxwidth == None:
            self._maxwidth = config.get_int ('maxwidth', 150)
        else:
            self._maxwidth = int("%s" % maxwidth)
        if maxheight == None:
            self._maxheight = config.get_int ('maxheight', 150)
        else:
            self._maxheight = int("%s" % maxheight)
        # Create Temp Files
        self._temp_files = self.CreateTempFiles(3)
        # Some globals
        self._scale_step = 10          # Start with 100%, then 90% ...
        self._org_width = 0            # There will be the orginal width of the input file later
        self._org_height = 0           # There will be the orginal heifht of the input file later


        # write the data to the in temp file
        f = open (self._temp_files[0], "wb")
        f.write (data)
        f.close ()


        self._org_width, self._org_height = self.convert_to_bmp(self._temp_files[0], self._temp_files[1])


        if self._guess_tbmp_size == 0:
            data = self.convert_to_Tbmp(self._temp_files[1], self._temp_files[2])
            if self._try_reduce_bpp and (len(data) > self._max_tbmp_size):
                while (len(data) > self._max_tbmp_size) and (self._bpp > 1):
                    self._bpp = self._bpp / 2
                    if self._verbose > 1:
                        print "Bitmap to large, try with bpp: %s" % self._bpp
                    data = self.convert_to_Tbmp(self._temp_files[1], self._temp_files[2])
            if self._try_reduce_dimension and (len(data) > self._max_tbmp_size):
                while (len(data) > self._max_tbmp_size) and (self._scale_step > 1):
                    self._scale_step = self._scale_step - 1
                    if self._verbose > 1:
                        print "Bitmap to large, try with scale: %s%%" % (self._scale_step * 10)
                    data = self.convert_to_Tbmp(self._temp_files[1], self._temp_files[2])
        else:
            if self._try_reduce_bpp:
                guessed_size = self.fake_convert_to_Tbmp()
                if self._verbose > 2:
                    print "Guessed TBmp Size: %s Bytes" % guessed_size
                while ( guessed_size > self._max_tbmp_size) and (self._bpp > 1):
                    self._bpp = self._bpp / 2
                    if self._verbose > 1:
                        print "Bitmap to large, try with bpp: %s" % self._bpp
                    guessed_size = self.fake_convert_to_Tbmp()
                    if self._verbose > 2:
                        print "Guessed TBmp Size: %s Bytes" % guessed_size
            if self._try_reduce_dimension and (len(data) > self._max_tbmp_size):
                guessed_size = self.fake_convert_to_Tbmp()
                if self._verbose > 2:
                    print "Guessed TBmp Size: %s Bytes" % guessed_size
                while (guessed_size > self._max_tbmp_size) and (self._scale_step > 1):
                    self._scale_step = self._scale_step - 1
                    if self._verbose > 1:
                        print "Bitmap to large, try with scale: %s%%" % (self._scale_step * 10)
                    guessed_size = self.fake_convert_to_Tbmp()
                    if self._verbose > 2:
                        print "Guessed TBmp Size: %s Bytes" % guessed_size
            data = self.convert_to_Tbmp(self._temp_files[1], self._temp_files[2])


        if len(data) > self._max_tbmp_size:
            raise RuntimeError, "\nImage too large (Size: %s, Maximum: %s)\n" % (len(data), self._max_tbmp_size)

        if self._verbose > 2:
            print "Resulting Tbmp Size: %s" % len(data)

        self._doc = PluckerDocs.PluckerImageDocument (str (url), config)
        self._doc.set_data (data)
        size = (ord(data[0]) * 256 + ord(data[1]), ord(data[2]) * 256 + ord(data[3]))


    def scale(self, width, height):
        if (width > self._maxwidth) or (height > self._maxheight):
            maxwidth = self._maxwidth
            maxheight = self._maxheight
        else:
            maxwidth = width
            maxheight = height

        new_width = (float(self._scale_step) / 10) * maxwidth
        new_height = (float(self._scale_step) / 10) * maxheight
        if (int(new_width) == 0):
            new_width = 1
        if (int(new_height) == 0):
            new_height = 1

        return (int(new_width), int(new_height))



    def scale_down(self, width, height, maxwidth, maxheight):
        if width > maxwidth:
            height = (height * maxwidth) / width
            width = maxwidth;

        if height > self._maxheight:
            width = (width * maxheight) / height
            height = maxheight;

        return width, height



    def calc_tbmp_size(self, width, height):
        if operator.mod(width * (float(self._bpp) / 8), 2):
            size = int(width * (float(self._bpp) / 8)) + 1
        else:
            size = int(width * (float(self._bpp) / 8))
        if operator.mod(size, 2):
            size = size + 1
        size = (size * height) + 16
        return size



    def convert_to_bmp(self, input_filename, output_filename):
        command = self.ReplaceVariables(self._imagemagick, input_filename, output_filename)
        if self._verbose > 1:
            print "Running %s" % command
        if self._verbose < 2:
            command = command + " > nul"
        res = os.system (command)
        if res:
            raise RuntimeError, "\nCommand %s failed with code %d\n" % (command, res)

        f = open (output_filename, "rb")
        data = f.read ()
        f.close ()

        if len(data) < 26:
            raise RuntimeError, "\nInvalid bitmap file\n"

        width = (ord(data[21]) << 24) + (ord(data[20]) << 16) + (ord(data[19]) << 8) + ord(data[18])
        height = (ord(data[25]) << 24) + (ord(data[24]) << 16) + (ord(data[23]) << 8) + ord(data[22])

        if self._verbose > 2:
            print "Original Bitmap Width: %s x %s" % (width, height)

        return width, height



    def fake_convert_to_Tbmp(self):
        (maxwidth, maxheight) = self.scale(self._org_width, self._org_height)
        (width, height) = self.scale_down(self._org_width, self._org_height, maxwidth, maxheight)
        return self.calc_tbmp_size(width, height)



    def convert_to_Tbmp(self, mid_name, out_name):
        (maxwidth, maxheight) = self.scale(self._org_width, self._org_height)
        command = self.ReplaceVariables(self._bmp2tbmp, mid_name, out_name, maxwidth, maxheight)
        if self._verbose < 2:
            command = command + " > nul"
        if self._verbose > 1:
            print "Running %s" % command
        res = os.system (command)
        if res:
            raise RuntimeError, "\nCommand %s failed with code %d\n" % (command, res)

        f = open (out_name, "rb")
        tbmp_data = f.read ()
        f.close ()

        if len(tbmp_data) < 4:
            raise RuntimeError, "\nInvalid tbmp file\n"

        tbmp_width = (ord(tbmp_data[0]) << 8) + ord(tbmp_data[1])
        tbmp_height = (ord(tbmp_data[2]) << 8) + ord(tbmp_data[3])

        if self._verbose > 2:
            print "TBmp Size: %sx%s" % (tbmp_width, tbmp_height)

        if (self._org_width > self._maxwidth) or (self._org_height > self._maxheight):
            self._scaled = 1
            if self._verbose > 1:
                print "Bitmap scaled down from %sx%s to %sx%s" % (self._org_width, self._org_height, tbmp_width, tbmp_height)

        if self._verbose > 2:
            print "TBmp Size: %s Bytes" % len(tbmp_data)

        return tbmp_data



    def quotestr(self, path):
        out = string.strip(path)
        if (string.find(out,' ') != -1) and (string.find(out,'"') == -1):
            out = "\""+out+"\""
        return out



    def DeleteTempFiles(self, temp):
        for x in range(len(temp)):
            try:
                if self._verbose > 2:
                    print "Deleting Tempoary File: %s" % self._temp_files[x]
                os.unlink (self._temp_files[x])
            except:
                if self._verbose > 2:
                    print "   failed\n"
                pass



    def CreateTempFiles(self, count):
        temp_filenames = []
        ok = 1
        for x in range(count):
            try:
                temp_filenames.append(tempfile.mktemp ())
                f = open (temp_filenames[x], "wb")
                f.write ("Tmp")
                f.close ()
                if self._verbose > 2:
                    print "Creating Tempoary File: %s" % temp_filenames[x]
            except:
                ok = 0
                if self._verbose > 2:
                    print "Creating Tempoary File: %s   failed" % temp_filenames[x]
        if not ok:
            raise RuntimeError, "\nFailed to create the Tempoary files\n"
        return temp_filenames



    def ReplaceVariables(self, CommandLine, InputFile, OutputFile, maxwidth=0, maxheight=0):

        if self._compress:
            compress_str = self._config.get_string ('tbmp_compression_type','yes')
        else:
            compress_str = 'no'

        Line = CommandLine
        Line = string.replace (Line , '%compress%', compress_str)
        Line = string.replace (Line , '%colors%', "%s" % self._bpp)
        Line = string.replace (Line , '%maxwidth%', "%s" % maxwidth)
        Line = string.replace (Line , '%maxheight%', "%s" % maxheight)
        Line = string.replace (Line , '%input%', InputFile)
        Line = string.replace (Line , '%output%', OutputFile)
        return Line



    def get_plucker_doc(self):
        return self._doc



    def scaled(self):
        return self._scaled



def map_parser_name(name):
    parser = string.lower (name)
    if parser == "windows":
        return WindowsImageParser
    elif parser == "netpbm2":
        return NewNetPBMImageParser
    else:
        return None


if sys.platform == 'win32':
    DefaultParser = WindowsImageParser
else:
    DefaultParser = map_parser_name(DEFAULT_IMAGE_PARSER_SETTING)


def get_default_parser (config):
    parser = config.get_string ('image_parser')
    return (parser and map_parser_name(parser)) or DefaultParser


if __name__ == '__main__':
    # Called as a script
    print "This file currently does nothing when called as a script"

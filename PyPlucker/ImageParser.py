#!/usr/bin/env python
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

import os, sys, string, tempfile, re, io, operator, subprocess
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
            raise RuntimeError("Converted image size for %s is zero bytes. Nothing fetched?" % self._url)

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
        attrib_width = 'width' in self._attribs and is_int(self._attribs.get('width')) and int(self._attribs.get('width'))
        attrib_height = 'height' in self._attribs and is_int(self._attribs.get('height')) and int(self._attribs.get('height'))
        versions = self._related_images(width < (attrib_width or (section and section[2]) or full_width) or
                                        height < (attrib_height or (section and section[3]) or full_height))
        list(map(lambda x, doc=doc: doc.add_related_image(x[0], x[1]), versions))
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

        cols = int(width / wide)
        if width % wide:
            cols = cols + 1

        rows = int(height / high)
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
        list(map(lambda x, doc=doc: doc.add_related_image(x[0], x[1]), versions))
        return doc

class PillowImageParser(ImageParser):

    "Convert an image to the PalmBitmap. Uses Python Imaging Library."

    def __init__(self, url, type, data, config, attribs, compress=1):
        from PIL import Image
        import PyPlucker.PalmImagePlugin

        ImageParser.__init__(self, url, type, data, config, attribs)
        try:
            self._image = Image.open (io.BytesIO(data))
        except:
            if self._verbose > 1:
                import traceback
                traceback.print_exc()
            raise RuntimeError("Error while opening image " + self._url + " with PIL")

    def _convert_to_Tbmp(self, im, pil_mode, bpp):
        from PyPlucker.PalmImagePlugin import Palm8BitColormapImage

        palmdata = io.BytesIO()
        if pil_mode == "1" or bpp == 1:
            im.convert("L").convert("1").save(palmdata, "Palm", bpp=bpp)
        elif pil_mode == "L":
            im.convert(pil_mode).save(palmdata, "Palm", bpp=bpp)
        elif pil_mode == "P" and bpp == 8:
            im.convert("RGB").quantize(palette=Palm8BitColormapImage).save(palmdata, "Palm", bpp=8)
        elif pil_mode == "RGB" and bpp == 16:
            im.convert("RGB").save(palmdata, "Palm", bpp=bpp)
        else:
            raise KeyError("Unsupported PIL mode " + pil_mode + " passed to convert.Tbmp")
        data = palmdata.getvalue()
        palmdata.close()
        return data

    def size(self):
        return self._image.size

    def convert(self, width, height, bpp, section, prescale=None):
        try:
            im = self._image
            if prescale:
                im = im.resize(prescale)
            if section:
                im = im.crop((section[0], section[1],
                                       section[0] + section[2], section[1] + section[3]))
            if width != im.size[0] or height != im.size[1]:
                message(2, "Scaling original %dx%d image by %f to %dx%dx%d" % (im.size[0], im.size[1], float(width)/float(im.size[0]), width, height, bpp))
                im = im.resize((width, height))
            if bpp == 1:
                return self._convert_to_Tbmp (im, "1", 1)
            elif bpp in (2, 4):
                return self._convert_to_Tbmp (im, "L", bpp)
            elif bpp == 8:
                return self._convert_to_Tbmp (im, "P", bpp)
            elif bpp == 16:
                return self._convert_to_Tbmp (im, "RGB", bpp)
            else:
                message(0, "%d bpp images not supported with PIL imaging yet.  Using 4 bpp grayscale.\n" % (bpp,))
                return self._convert_to_Tbmp (im, "L", 4)
        except:
            if self._verbose > 1:
                import traceback
                traceback.print_exc()
            raise RuntimeError("Error while converting image " + self._url + " with PIL")

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
            command = djpeg + ' -pnm' # make command an array
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
                if self._verbose > 1:
                    message(2, "Running:  " + command)

                p = subprocess.run(command.split(' '), input=self._bits, capture_output=True)

                f = open(self._tmpfile, 'wb')
                f.write(p.stdout)
                f.close()

                status = p.returncode

                if status != 0:
                    raise RuntimeError("call to '" + command + "' returned status " + str(status))
                f = open(self._tmpfile, 'rb')
                self._pnmdata = f.read()
                f.close()
            finally:
                if os.path.exists(self._tmpfile): os.unlink(self._tmpfile)

        # now read the width and height from the PNM data
        m = pnmheader_pattern.match(self._pnmdata.decode('latin-1'))
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

        if self._verbose > 1:
            message(2, "Running:  " + command)

        try:
            p = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
            out, err = p.communicate(input=self._pnmdata)

            f = open(self._tmpfile, 'wb')
            f.write(out)
            f.close()

            if p.returncode != 0:
                raise RuntimeError("call to '" + command + "' returned status " + str(p.returncode))
            f = open(self._tmpfile, 'rb')
            newbits = f.read()
            f.close()
            return newbits
        finally:
            if os.path.exists(self._tmpfile): os.unlink(self._tmpfile)

# TODO: Delete since we only have 1 parser at the moment
def map_parser_name(name):
    parser = name.lower()
    if parser == "netpbm2":
        return NewNetPBMImageParser
    elif parser == "pillow":
        return PillowImageParser
    else:
        return None

DefaultParser = map_parser_name(DEFAULT_IMAGE_PARSER_SETTING)

def get_default_parser (config):
    parser = config.get_string ('image_parser')
    return (parser and map_parser_name(parser)) or DefaultParser


if __name__ == '__main__':
    # Called as a script
    print("This file currently does nothing when called as a script")

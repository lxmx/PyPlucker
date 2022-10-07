# PyPlucker

![Palm OS](https://img.shields.io/badge/Palm%20OS-%3E%3D%202.0-blue) [![PyPI](https://img.shields.io/pypi/pyversions/PyPlucker.svg)](https://pypi.python.org/pypi/PyPlucker)

It's 2022 and you need a Palm again!

This is an updated version of the original Python based Plucker parser. It downloads and converts your favorite web pages and local files for the [Plucker app](https://palmdb.net/app/plucker).

<img src="https://user-images.githubusercontent.com/58649917/153739856-226c672f-bfb9-4436-ac2d-de79e63a4e3c.png" width=320/>

Some of the updates are:

* The code has been ported to **Python 3**
* The default image parser is now based on [Pillow](https://python-pillow.org/) which doesn't require any platform native dependencies and adds WebP support as a bonus.
* Some legacy bits have been removed: OS/2 support, non-working image parser versions

## Installation

```
pip install PyPlucker
```

Optionally, install the example [~/.pluckerrc config](https://github.com/lxmx/PyPlucker/blob/master/examples/pluckerrc) and a [~/.plucker/home.html](https://raw.githubusercontent.com/lxmx/PyPlucker/master/examples/home.html) index file.

## Usage 

For example, running the below:

```
plucker-build -H http://www.floodgap.com/retrotech/plua/ -M 1 -f Plua_Revisited --bpp=4 --maxwidth=150

```

Will:

1. Download the `http://www.floodgap.com/retrotech/plua/` page and not follow any links in it, due to `-M 1` (i.e. `--maxdepth=1`)
3. Convert all the graphics to 16 shades of gray due to `bpp=4` and resize to 150 pixels of maximum width (`maxwidth=150`)
4. Produce a file called `Plua_Revisited.pdb` in the `~/.plucker` directory

See `~/.pluckerrc` for more options and parameters.

### Notes

#### Complex pages

For best results, it's a good idea to run more complex pages through a modern Readability filter like [percollate](https://github.com/danburzo/percollate) first. See a [working example script](https://github.com/lxmx/PyPlucker/blob/master/examples/pluck.sh).

#### Compatibility

* PyPlucker produced documents are known to be compatible with the Palm OS Plucker application versions 1.2 and above.
* For Palm OS 3.0 and above you can use the `--compression=zlib` option to make the output files much smaller. Make sure that you install `SysZLib.prc` first.

### References

* Original [Python 2 version](https://github.com/lxmx/PyPlucker/tree/python2)
* [Full original source](https://github.com/arpruss/plucker) code for all Plucker components
* [Plucker's cool old website](https://web.archive.org/web/20160415203050/http://www.plkr.org/) on web.archive.org


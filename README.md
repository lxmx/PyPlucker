# PyPlucker

It's 2022 and you need a Palm!

This is an updated version of the Python based Plucker parser from the [original repository](https://github.com/arpruss/plucker). The parser downloads your favorite web pages or converts local files for the [Plucker app](https://palmdb.net/app/plucker).

<img src="https://user-images.githubusercontent.com/58649917/153739856-226c672f-bfb9-4436-ac2d-de79e63a4e3c.png" width=320/>

Updates from the original parser:

* Has been ported to Python 3
* Some legacy bits have been removed: OS/2 support, non-working image parser versions
* The default image parser is now based on [Pillow](https://python-pillow.org/) which doesn't require any third-party dependencies and adds WebP support as a bonus.

## Installation

```
pip install PyPlucker
```

Optionally, populate the example config file and `home.html`:

```
cp examples/pluckerrc ~/.pluckerrc
mkdir ~/.plucker
cp examples/home.html ~/.plucker/
```

## Usage 

```
plucker-build --bpp=4 --maxdepth=1 --doc-file=PythonCompileAllDoc -H https://docs.python.org/3/library/compileall.html

```

See `~/.pluckerrc` for the options and parameters.

### In Practice

Since it's been a while since Plucker's HTML processing and cleanup code was last updated, it's a good idea to run more complex pages through a modern Readability filter like [percollate](https://github.com/danburzo/percollate) first. See `examples/pluck.sh` for a working script.

### References

* Original [Python 2 version](https://github.com/lxmx/PyPlucker/tree/python3)


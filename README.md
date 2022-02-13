# PyPlucker

It's 2022 and you need a Palm!

This is an import of the Python based Plucker parser from the [original repository](https://github.com/arpruss/plucker). It's meant to work on a recent GNU/Linux distro.

I have also stripped some legacy bits like OS/2 support and broken image converter alternatives.

## Installation

Assuming Ubuntu 21.10 or similar. Otherwise you may want to edit the `Makefile`.

Clone the repository and:

```
sudo apt install python2.7 netbpm
sudo make install
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

See `~/.pluckerrc` for the options and parameters. Also see the excellent official documentation as supplied in the [Palm bundle](https://palmdb.net/app/plucker).

### In Practice

Since it's been a while since Plucker's HTML parser was last updated, it's a good idea to run more complex pages through a modern Readability filter like [percollate](https://github.com/danburzo/percollate) first. See `examples/pluck.sh` for a working script.

## TODO

- Port to Python3

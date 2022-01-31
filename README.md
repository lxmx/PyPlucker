# PyPlucker

It's 2022 and you need a Palm.

This is an import of the Python based Plucker parser from the [original repository](https://github.com/arpruss/plucker). It's meant to work on a recent GNU/Linux distro.

I have also stripped some legacy bits like OS/2 support and broken image converter alternatives.

## Installation

Assuming Ubuntu 21.10:

```
sudo apt install python2.7 netbpm
git clone https://github.com/vaskas/PyPlucker
sudo cp -R PyPlucker /usr/lib/python2.7/site-packages/
sudo ln -s /usr/lib/python2.7/site-packages/PyPlucker/Spider.py /usr/local/bin/plucker-build 
cp PyPlucker/pluckerrc.sample ~/.pluckerrc
```

## Usage example

```
plucker-build --bpp=4 --maxdepth=1 --doc-file=PythonCompileAllDoc -H https://docs.python.org/3/library/compileall.html

```

See `~/.pluckerrc` for the options and parameters. Also see the excellent official documentation as supplied in the [Palm bundle](https://palmdb.net/app/plucker).

## TODO

- Port to Python 3
- Package for PIP

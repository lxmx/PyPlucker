import os
from setuptools import setup, find_packages

def get_version(fname=os.path.join('PyPlucker', '__init__.py')):
    with open(fname) as f:
        for line in f:
            if line.startswith('__version__'):
                return eval(line.split('=')[-1])

def get_long_description():
    with open('README.md') as f:
        return f.read()

setup(
    name='PyPlucker',
    version=get_version(),
    license='GPLv2',
    author="Vasily Mikhaylichenko",
    author_email='vasily@lxmx.org',
    url='https://github.com/lxmx/PyPlucker',
    install_requires=[
          'Pillow',
    ],
    scripts=["bin/plucker-build"],
    packages=find_packages('.'),
    description='Web and document parser, converter and scraper for Plucker, the Palm OS app',
    long_description=get_long_description(),
    long_description_content_type='text/markdown',
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Operating System :: OS Independent",
        "Operating System :: PDA Systems",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Topic :: Utilities",
        "Topic :: Education",
        "Topic :: Text Processing",
        "Topic :: Multimedia :: Graphics :: Graphics Conversion",
    ],
)

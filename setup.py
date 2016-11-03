from sys import exit, version

from setuptools import setup

import bagit

if version < '2.6.0':
    print("python 2.6 or higher is required")
    exit(1)

description = \
"""
This package can be used to create BagIt style packages of
digital content for safe transmission and digital preservation.
See: http://en.wikipedia.org/wiki/BagIt for more details.
"""

# for older pythons ...
requirements = []
try:
    import multiprocessing
except:
    requirements.append("multiprocessing")
try:
    import hashlib
except:
    requirements.append("hashlib")

version = bagit.VERSION

setup(
    name = 'bagit',
    use_scm_version=True,
    url = 'https://libraryofcongress.github.io/bagit-python/',
    author = 'Ed Summers',
    author_email = 'ehs@pobox.com',
    py_modules = ['bagit',],
    scripts = ['bagit.py'],
    description = description,
    platforms = ['POSIX'],
    test_suite = 'test',
    setup_requires=['setuptools_scm'],
    tests_require=['mock'],
    install_requires = requirements,
    classifiers = [
        'License :: Public Domain',
        'Intended Audience :: Developers',
        'Topic :: Communications :: File Sharing',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Filesystems',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.1',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
)

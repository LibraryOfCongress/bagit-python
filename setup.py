#!/usr/bin/env python
# encoding: utf-8

from __future__ import absolute_import, print_function

import glob
import os
import subprocess
import sys
from setuptools import setup

if sys.version_info < (2, 6):
    print("Python 2.6 or higher is required")
    sys.exit(1)

description = 'Create and validate BagIt packages'

with open('README.rst') as readme:
    long_description = readme.read()

tests_require = ['mock', 'coverage']

if sys.version_info < (2, 7):
    tests_require.append('unittest2')


def get_message_catalogs():
    message_catalogs = []

    for po_file in glob.glob('locale/*/LC_MESSAGES/bagit-python.po'):
        mo_file = po_file.replace('.po', '.mo')

        if not os.path.exists(mo_file) or os.path.getmtime(mo_file) < os.path.getmtime(po_file):
            try:
                subprocess.check_call(['msgfmt', '-o', mo_file, po_file])
            except (OSError, subprocess.CalledProcessError) as exc:
                print("Translation catalog %s could not be compiled (is gettext installed?) "
                      " — translations will not be available for this language: %s" % (po_file, exc),
                      file=sys.stderr)
                continue

        message_catalogs.append((os.path.dirname(mo_file), (mo_file, )))

    return message_catalogs


setup(
    name='bagit',
    use_scm_version=True,
    url='https://libraryofcongress.github.io/bagit-python/',
    author='Ed Summers',
    author_email='ehs@pobox.com',
    py_modules=['bagit', ],
    scripts=['bagit.py'],
    data_files=get_message_catalogs(),
    description=description,
    long_description=long_description,
    platforms=['POSIX'],
    test_suite='test',
    setup_requires=['setuptools_scm'],
    tests_require=tests_require,
    classifiers=[
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
        'Programming Language :: Python :: 3.6',
    ],
)

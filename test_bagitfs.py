# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

import codecs
import datetime
import hashlib
import logging
import os
import shutil
import stat
import sys
import tempfile
import unicodedata
import unittest
from os.path import join as j

from unittest import mock

import bagitfs
import bagit
from test import SelfCleaningTestCase

from fs.zipfs import ZipFS

logging.basicConfig(filename="test.log", level=logging.DEBUG)
stderr = logging.StreamHandler()
stderr.setLevel(logging.WARNING)
logging.getLogger().addHandler(stderr)

# But we do want any exceptions raised in the logging path to be raised:
logging.raiseExceptions = True

@mock.patch(
    "bagit.VERSION", new="1.5.4"
)  # This avoids needing to change expected hashes on each release
class TestZipValidation(SelfCleaningTestCase):
    def test_wrong_bagit_zip_open(self):
        with ZipFS("./test-data.zip") as zip_fs:
            try:
                bag = bagitfs.BagitFs(zip_fs)
            except bagit.BagError as e:
                self.assertEqual("Expected bagit.txt does not exist: /bagit.txt", str(e))

    def test_correct_bagit_zip(self):
        bag = bagit.make_bag(self.tmpdir, checksum=["sha1", "sha256"])
        # check that relevant manifests are created
        self.assertTrue(os.path.isfile(j(self.tmpdir, "manifest-sha1.txt")))
        self.assertTrue(os.path.isfile(j(self.tmpdir, "manifest-sha256.txt")))

        shutil.make_archive(os.path.join(self.tmpdir, "bag-correct_zip"), 'zip', self.tmpdir)
        with ZipFS(os.path.join(self.tmpdir, "bag-correct_zip.zip")) as zip_fs:
            bag = bagitfs.BagitFs(zip_fs)
            bag.validate()

if __name__ == "__main__":
    unittest.main()

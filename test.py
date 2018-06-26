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

import mock

import bagit

logging.basicConfig(filename="test.log", level=logging.DEBUG)
stderr = logging.StreamHandler()
stderr.setLevel(logging.WARNING)
logging.getLogger().addHandler(stderr)

# But we do want any exceptions raised in the logging path to be raised:
logging.raiseExceptions = True


def slurp_text_file(filename):
    with bagit.open_text_file(filename) as f:
        return f.read()


class SelfCleaningTestCase(unittest.TestCase):
    """TestCase subclass which cleans up self.tmpdir after each test"""

    def setUp(self):
        super(SelfCleaningTestCase, self).setUp()

        self.starting_directory = (
            os.getcwd()
        )  # FIXME: remove this after we stop changing directories in bagit.py
        self.tmpdir = tempfile.mkdtemp()
        if os.path.isdir(self.tmpdir):
            shutil.rmtree(self.tmpdir)
        shutil.copytree("test-data", self.tmpdir)

    def tearDown(self):
        # FIXME: remove this after we stop changing directories in bagit.py
        os.chdir(self.starting_directory)
        if os.path.isdir(self.tmpdir):
            # Clean up after tests which leave inaccessible files behind:

            os.chmod(self.tmpdir, 0o700)

            for dirpath, subdirs, filenames in os.walk(self.tmpdir, topdown=True):
                for i in subdirs:
                    os.chmod(os.path.join(dirpath, i), 0o700)

            shutil.rmtree(self.tmpdir)

        super(SelfCleaningTestCase, self).tearDown()


@mock.patch(
    "bagit.VERSION", new="1.5.4"
)  # This avoids needing to change expected hashes on each release
class TestSingleProcessValidation(SelfCleaningTestCase):
    def validate(self, bag, *args, **kwargs):
        return bag.validate(*args, **kwargs)

    def test_make_bag_sha1_sha256_manifest(self):
        bag = bagit.make_bag(self.tmpdir, checksum=["sha1", "sha256"])
        # check that relevant manifests are created
        self.assertTrue(os.path.isfile(j(self.tmpdir, "manifest-sha1.txt")))
        self.assertTrue(os.path.isfile(j(self.tmpdir, "manifest-sha256.txt")))
        # check valid with two manifests
        self.assertTrue(self.validate(bag, fast=True))

    def test_make_bag_md5_sha256_manifest(self):
        bag = bagit.make_bag(self.tmpdir, checksum=["md5", "sha256"])
        # check that relevant manifests are created
        self.assertTrue(os.path.isfile(j(self.tmpdir, "manifest-md5.txt")))
        self.assertTrue(os.path.isfile(j(self.tmpdir, "manifest-sha256.txt")))
        # check valid with two manifests
        self.assertTrue(self.validate(bag, fast=True))

    def test_make_bag_md5_sha1_sha256_manifest(self):
        bag = bagit.make_bag(self.tmpdir, checksum=["md5", "sha1", "sha256"])
        # check that relevant manifests are created
        self.assertTrue(os.path.isfile(j(self.tmpdir, "manifest-md5.txt")))
        self.assertTrue(os.path.isfile(j(self.tmpdir, "manifest-sha1.txt")))
        self.assertTrue(os.path.isfile(j(self.tmpdir, "manifest-sha256.txt")))
        # check valid with three manifests
        self.assertTrue(self.validate(bag, fast=True))

    def test_validate_flipped_bit(self):
        bag = bagit.make_bag(self.tmpdir)
        readme = j(self.tmpdir, "data", "README")
        txt = slurp_text_file(readme)
        txt = "A" + txt[1:]
        with open(readme, "w") as r:
            r.write(txt)
        bag = bagit.Bag(self.tmpdir)
        self.assertRaises(bagit.BagValidationError, self.validate, bag)
        # fast doesn't catch the flipped bit, since oxsum is the same
        self.assertTrue(self.validate(bag, fast=True))
        self.assertTrue(self.validate(bag, completeness_only=True))

    def test_validate_fast(self):
        bag = bagit.make_bag(self.tmpdir)
        self.assertEqual(self.validate(bag, fast=True), True)
        os.remove(j(self.tmpdir, "data", "loc", "2478433644_2839c5e8b8_o_d.jpg"))
        self.assertRaises(bagit.BagValidationError, self.validate, bag, fast=True)

    def test_validate_completeness(self):
        bag = bagit.make_bag(self.tmpdir)
        old_path = j(self.tmpdir, "data", "README")
        new_path = j(self.tmpdir, "data", "extra_file")
        os.rename(old_path, new_path)
        bag = bagit.Bag(self.tmpdir)
        self.assertTrue(self.validate(bag, fast=True))
        with mock.patch.object(bag, "_validate_entries") as m:
            self.assertRaises(
                bagit.BagValidationError, self.validate, bag, completeness_only=True
            )
            self.assertEqual(m.call_count, 0)

    def test_validate_fast_without_oxum(self):
        bag = bagit.make_bag(self.tmpdir)
        os.remove(j(self.tmpdir, "bag-info.txt"))
        bag = bagit.Bag(self.tmpdir)
        self.assertRaises(bagit.BagValidationError, self.validate, bag, fast=True)

    def test_validate_slow_without_oxum_extra_file(self):
        bag = bagit.make_bag(self.tmpdir)
        os.remove(j(self.tmpdir, "bag-info.txt"))
        with open(j(self.tmpdir, "data", "extra_file"), "w") as ef:
            ef.write("foo")
        bag = bagit.Bag(self.tmpdir)
        self.assertRaises(bagit.BagValidationError, self.validate, bag, fast=False)

    def test_validate_missing_directory(self):
        bagit.make_bag(self.tmpdir)

        tmp_data_dir = os.path.join(self.tmpdir, "data")
        shutil.rmtree(tmp_data_dir)

        bag = bagit.Bag(self.tmpdir)
        with self.assertRaises(bagit.BagValidationError) as error_catcher:
            bag.validate()

        self.assertEqual(
            "Expected data directory %s does not exist" % tmp_data_dir,
            str(error_catcher.exception),
        )

    def test_validation_error_details(self):
        bag = bagit.make_bag(
            self.tmpdir, checksums=["md5"], bag_info={"Bagging-Date": "1970-01-01"}
        )
        readme = j(self.tmpdir, "data", "README")
        txt = slurp_text_file(readme)
        txt = "A" + txt[1:]
        with open(readme, "w") as r:
            r.write(txt)

        bag = bagit.Bag(self.tmpdir)
        got_exception = False

        try:
            self.validate(bag)
        except bagit.BagValidationError as e:
            got_exception = True

            exc_str = str(e)
            self.assertIn(
                'data/README md5 validation failed: expected="8e2af7a0143c7b8f4de0b3fc90f27354" found="fd41543285d17e7c29cd953f5cf5b955"',
                exc_str,
            )
            self.assertEqual(len(e.details), 1)

            readme_error = e.details[0]
            self.assertEqual(
                'data/README md5 validation failed: expected="8e2af7a0143c7b8f4de0b3fc90f27354" found="fd41543285d17e7c29cd953f5cf5b955"',
                str(readme_error),
            )
            self.assertIsInstance(readme_error, bagit.ChecksumMismatch)
            self.assertEqual(readme_error.algorithm, "md5")
            self.assertEqual(readme_error.path, "data/README")
            self.assertEqual(readme_error.expected, "8e2af7a0143c7b8f4de0b3fc90f27354")
            self.assertEqual(readme_error.found, "fd41543285d17e7c29cd953f5cf5b955")

        if not got_exception:
            self.fail("didn't get BagValidationError")

    def test_validation_completeness_error_details(self):
        bag = bagit.make_bag(
            self.tmpdir, checksums=["md5"], bag_info={"Bagging-Date": "1970-01-01"}
        )

        old_path = j(self.tmpdir, "data", "README")
        new_path = j(self.tmpdir, "data", "extra")
        os.rename(old_path, new_path)

        # remove the bag-info.txt which contains the oxum to force a full
        # check of the manifest
        os.remove(j(self.tmpdir, "bag-info.txt"))

        bag = bagit.Bag(self.tmpdir)
        got_exception = False

        try:
            self.validate(bag)
        except bagit.BagValidationError as e:
            got_exception = True

            exc_str = str(e)
            self.assertIn("Bag validation failed: ", exc_str)
            self.assertIn(
                "bag-info.txt exists in manifest but was not found on filesystem",
                exc_str,
            )
            self.assertIn(
                "data/README exists in manifest but was not found on filesystem",
                exc_str,
            )
            self.assertIn(
                "data/extra exists on filesystem but is not in the manifest", exc_str
            )
            self.assertEqual(len(e.details), 3)

            if e.details[0].path == "bag-info.txt":
                baginfo_error = e.details[0]
                readme_error = e.details[1]
            else:
                baginfo_error = e.details[1]
                readme_error = e.details[0]

            self.assertEqual(
                str(baginfo_error),
                "bag-info.txt exists in manifest but was not found on filesystem",
            )
            self.assertIsInstance(baginfo_error, bagit.FileMissing)
            self.assertEqual(baginfo_error.path, "bag-info.txt")

            self.assertEqual(
                str(readme_error),
                "data/README exists in manifest but was not found on filesystem",
            )
            self.assertIsInstance(readme_error, bagit.FileMissing)
            self.assertEqual(readme_error.path, "data/README")

            error = e.details[2]
            self.assertEqual(
                str(error), "data/extra exists on filesystem but is not in the manifest"
            )
            self.assertTrue(error, bagit.UnexpectedFile)
            self.assertEqual(error.path, "data/extra")

        if not got_exception:
            self.fail("didn't get BagValidationError")

    def test_bom_in_bagit_txt(self):
        bag = bagit.make_bag(self.tmpdir)
        BOM = codecs.BOM_UTF8
        if sys.version_info[0] >= 3:
            BOM = BOM.decode("utf-8")
        with open(j(self.tmpdir, "bagit.txt"), "r") as bf:
            bagfile = BOM + bf.read()
        with open(j(self.tmpdir, "bagit.txt"), "w") as bf:
            bf.write(bagfile)
        bag = bagit.Bag(self.tmpdir)
        self.assertRaises(bagit.BagValidationError, self.validate, bag)

    def test_missing_file(self):
        bag = bagit.make_bag(self.tmpdir)
        os.remove(j(self.tmpdir, "data", "loc", "3314493806_6f1db86d66_o_d.jpg"))
        self.assertRaises(bagit.BagValidationError, self.validate, bag)

    def test_handle_directory_end_slash_gracefully(self):
        bag = bagit.make_bag(self.tmpdir + "/")
        self.assertTrue(self.validate(bag))
        bag2 = bagit.Bag(self.tmpdir + "/")
        self.assertTrue(self.validate(bag2))

    def test_allow_extraneous_files_in_base(self):
        bag = bagit.make_bag(self.tmpdir)
        self.assertTrue(self.validate(bag))
        f = j(self.tmpdir, "IGNOREFILE")
        with open(f, "w"):
            self.assertTrue(self.validate(bag))

    def test_allow_extraneous_dirs_in_base(self):
        bag = bagit.make_bag(self.tmpdir)
        self.assertTrue(self.validate(bag))
        d = j(self.tmpdir, "IGNOREDIR")
        os.mkdir(d)
        self.assertTrue(self.validate(bag))

    def test_missing_tagfile_raises_error(self):
        bag = bagit.make_bag(self.tmpdir)
        self.assertTrue(self.validate(bag))
        os.remove(j(self.tmpdir, "bagit.txt"))
        self.assertRaises(bagit.BagValidationError, self.validate, bag)

    def test_missing_manifest_raises_error(self):
        bag = bagit.make_bag(self.tmpdir, checksums=["sha512"])
        self.assertTrue(self.validate(bag))
        os.remove(j(self.tmpdir, "manifest-sha512.txt"))
        self.assertRaises(bagit.BagValidationError, self.validate, bag)

    def test_mixed_case_checksums(self):
        bag = bagit.make_bag(self.tmpdir, checksums=["md5"])
        hashstr = {}
        # Extract entries only for the payload and ignore
        # entries from the tagmanifest file
        for key in bag.entries.keys():
            if key.startswith("data" + os.sep):
                hashstr = bag.entries[key]
        hashstr = next(iter(hashstr.values()))
        manifest = slurp_text_file(j(self.tmpdir, "manifest-md5.txt"))

        manifest = manifest.replace(hashstr, hashstr.upper())

        with open(j(self.tmpdir, "manifest-md5.txt"), "wb") as m:
            m.write(manifest.encode("utf-8"))

        # Since manifest-md5.txt file is updated, re-calculate its
        # md5 checksum and update it in the tagmanifest-md5.txt file
        hasher = hashlib.new("md5")
        contents = slurp_text_file(j(self.tmpdir, "manifest-md5.txt")).encode("utf-8")
        hasher.update(contents)
        with open(j(self.tmpdir, "tagmanifest-md5.txt"), "r") as tagmanifest:
            tagman_contents = tagmanifest.read()
            tagman_contents = tagman_contents.replace(
                bag.entries["manifest-md5.txt"]["md5"], hasher.hexdigest()
            )
        with open(j(self.tmpdir, "tagmanifest-md5.txt"), "w") as tagmanifest:
            tagmanifest.write(tagman_contents)

        bag = bagit.Bag(self.tmpdir)
        self.assertTrue(self.validate(bag))

    def test_unsafe_directory_entries_raise_error(self):
        bad_paths = None
        # This could be more granular, but ought to be
        # adequate.
        if os.name == "nt":
            bad_paths = (
                r"C:\win32\cmd.exe",
                "\\\\?\\C:\\",
                "COM1:",
                "\\\\.\\COM56",
                "..\\..\\..\\win32\\cmd.exe",
                "data\\..\\..\\..\\win32\\cmd.exe",
            )
        else:
            bad_paths = (
                "../../../secrets.json",
                "~/.pgp/id_rsa",
                "/dev/null",
                "data/../../../secrets.json",
            )
        hasher = hashlib.new("md5")
        corpus = "this is not a real checksum"
        hasher.update(corpus.encode("utf-8"))
        for bad_path in bad_paths:
            bagit.make_bag(self.tmpdir, checksums=["md5"])
            with open(j(self.tmpdir, "manifest-md5.txt"), "wb+") as manifest_out:
                line = "%s %s\n" % (hasher.hexdigest(), bad_path)
                manifest_out.write(line.encode("utf-8"))
            self.assertRaises(bagit.BagError, bagit.Bag, self.tmpdir)

    def test_multiple_oxum_values(self):
        bag = bagit.make_bag(self.tmpdir)
        with open(j(self.tmpdir, "bag-info.txt"), "a") as baginfo:
            baginfo.write("Payload-Oxum: 7.7\n")
        bag = bagit.Bag(self.tmpdir)
        self.assertTrue(self.validate(bag, fast=True))

    def test_validate_optional_tagfile(self):
        bag = bagit.make_bag(self.tmpdir, checksums=["md5"])
        tagdir = tempfile.mkdtemp(dir=self.tmpdir)
        with open(j(tagdir, "tagfile"), "w") as tagfile:
            tagfile.write("test")
        relpath = j(tagdir, "tagfile").replace(self.tmpdir + os.sep, "")
        relpath.replace("\\", "/")
        with open(j(self.tmpdir, "tagmanifest-md5.txt"), "w") as tagman:
            # Incorrect checksum.
            tagman.write("8e2af7a0143c7b8f4de0b3fc90f27354 " + relpath + "\n")
        bag = bagit.Bag(self.tmpdir)
        self.assertRaises(bagit.BagValidationError, self.validate, bag)

        hasher = hashlib.new("md5")
        contents = slurp_text_file(j(tagdir, "tagfile")).encode("utf-8")
        hasher.update(contents)
        with open(j(self.tmpdir, "tagmanifest-md5.txt"), "w") as tagman:
            tagman.write(hasher.hexdigest() + " " + relpath + "\n")
        bag = bagit.Bag(self.tmpdir)
        self.assertTrue(self.validate(bag))

        # Missing tagfile.
        os.remove(j(tagdir, "tagfile"))
        bag = bagit.Bag(self.tmpdir)
        self.assertRaises(bagit.BagValidationError, self.validate, bag)

    def test_validate_optional_tagfile_in_directory(self):
        bag = bagit.make_bag(self.tmpdir, checksums=["md5"])
        tagdir = tempfile.mkdtemp(dir=self.tmpdir)

        if not os.path.exists(j(tagdir, "tagfolder")):
            os.makedirs(j(tagdir, "tagfolder"))

        with open(j(tagdir, "tagfolder", "tagfile"), "w") as tagfile:
            tagfile.write("test")
        relpath = j(tagdir, "tagfolder", "tagfile").replace(self.tmpdir + os.sep, "")
        relpath.replace("\\", "/")
        with open(j(self.tmpdir, "tagmanifest-md5.txt"), "w") as tagman:
            # Incorrect checksum.
            tagman.write("8e2af7a0143c7b8f4de0b3fc90f27354 " + relpath + "\n")
        bag = bagit.Bag(self.tmpdir)
        self.assertRaises(bagit.BagValidationError, self.validate, bag)

        hasher = hashlib.new("md5")
        with open(j(tagdir, "tagfolder", "tagfile"), "r") as tf:
            contents = tf.read().encode("utf-8")
        hasher.update(contents)
        with open(j(self.tmpdir, "tagmanifest-md5.txt"), "w") as tagman:
            tagman.write(hasher.hexdigest() + " " + relpath + "\n")
        bag = bagit.Bag(self.tmpdir)
        self.assertTrue(self.validate(bag))

        # Missing tagfile.
        os.remove(j(tagdir, "tagfolder", "tagfile"))
        bag = bagit.Bag(self.tmpdir)
        self.assertRaises(bagit.BagValidationError, self.validate, bag)

    def test_sha1_tagfile(self):
        info = {"Bagging-Date": "1970-01-01", "Contact-Email": "ehs@pobox.com"}
        bag = bagit.make_bag(self.tmpdir, checksum=["sha1"], bag_info=info)
        self.assertTrue(os.path.isfile(j(self.tmpdir, "tagmanifest-sha1.txt")))
        self.assertEqual(
            "f69110479d0d395f7c321b3860c2bc0c96ae9fe8",
            bag.entries["bag-info.txt"]["sha1"],
        )

    def test_validate_unreadable_file(self):
        bag = bagit.make_bag(self.tmpdir, checksum=["md5"])
        os.chmod(j(self.tmpdir, "data/loc/2478433644_2839c5e8b8_o_d.jpg"), 0)
        self.assertRaises(bagit.BagValidationError, self.validate, bag, fast=False)


class TestMultiprocessValidation(TestSingleProcessValidation):
    def validate(self, bag, *args, **kwargs):
        return super(TestMultiprocessValidation, self).validate(
            bag, *args, processes=2, **kwargs
        )


@mock.patch(
    "bagit.VERSION", new="1.5.4"
)  # This avoids needing to change expected hashes on each release
class TestBag(SelfCleaningTestCase):
    def test_make_bag(self):
        info = {"Bagging-Date": "1970-01-01", "Contact-Email": "ehs@pobox.com"}
        bagit.make_bag(self.tmpdir, bag_info=info, checksums=["md5"])

        # data dir should've been created
        self.assertTrue(os.path.isdir(j(self.tmpdir, "data")))

        # check bagit.txt
        self.assertTrue(os.path.isfile(j(self.tmpdir, "bagit.txt")))
        bagit_txt = slurp_text_file(j(self.tmpdir, "bagit.txt"))
        self.assertTrue("BagIt-Version: 0.97", bagit_txt)
        self.assertTrue("Tag-File-Character-Encoding: UTF-8", bagit_txt)

        # check manifest
        self.assertTrue(os.path.isfile(j(self.tmpdir, "manifest-md5.txt")))
        manifest_txt = slurp_text_file(j(self.tmpdir, "manifest-md5.txt")).splitlines()
        self.assertIn("8e2af7a0143c7b8f4de0b3fc90f27354  data/README", manifest_txt)
        self.assertIn(
            "9a2b89e9940fea6ac3a0cc71b0a933a0  data/loc/2478433644_2839c5e8b8_o_d.jpg",
            manifest_txt,
        )
        self.assertIn(
            "6172e980c2767c12135e3b9d246af5a3  data/loc/3314493806_6f1db86d66_o_d.jpg",
            manifest_txt,
        )
        self.assertIn(
            "38a84cd1c41de793a0bccff6f3ec8ad0  data/si/2584174182_ffd5c24905_b_d.jpg",
            manifest_txt,
        )
        self.assertIn(
            "5580eaa31ad1549739de12df819e9af8  data/si/4011399822_65987a4806_b_d.jpg",
            manifest_txt,
        )

        # check bag-info.txt
        self.assertTrue(os.path.isfile(j(self.tmpdir, "bag-info.txt")))
        bag_info_txt = slurp_text_file(j(self.tmpdir, "bag-info.txt"))
        bag_info_txt = bag_info_txt.splitlines()
        self.assertIn("Contact-Email: ehs@pobox.com", bag_info_txt)
        self.assertIn("Bagging-Date: 1970-01-01", bag_info_txt)
        self.assertIn("Payload-Oxum: 991765.5", bag_info_txt)
        self.assertIn(
            "Bag-Software-Agent: bagit.py v1.5.4 <https://github.com/LibraryOfCongress/bagit-python>",
            bag_info_txt,
        )

        # check tagmanifest-md5.txt
        self.assertTrue(os.path.isfile(j(self.tmpdir, "tagmanifest-md5.txt")))
        tagmanifest_txt = slurp_text_file(
            j(self.tmpdir, "tagmanifest-md5.txt")
        ).splitlines()
        self.assertIn("9e5ad981e0d29adc278f6a294b8c2aca bagit.txt", tagmanifest_txt)
        self.assertIn(
            "a0ce6631a2a6d1a88e6d38453ccc72a5 manifest-md5.txt", tagmanifest_txt
        )
        self.assertIn("0a6ffcffe67e9a34e44220f7ebcb4baa bag-info.txt", tagmanifest_txt)

    def test_make_bag_sha1_manifest(self):
        bagit.make_bag(self.tmpdir, checksum=["sha1"])
        # check manifest
        self.assertTrue(os.path.isfile(j(self.tmpdir, "manifest-sha1.txt")))
        manifest_txt = slurp_text_file(j(self.tmpdir, "manifest-sha1.txt")).splitlines()
        self.assertIn(
            "ace19416e605cfb12ab11df4898ca7fd9979ee43  data/README", manifest_txt
        )
        self.assertIn(
            "4c0a3da57374e8db379145f18601b159f3cad44b  data/loc/2478433644_2839c5e8b8_o_d.jpg",
            manifest_txt,
        )
        self.assertIn(
            "62095aeddae2f3207cb77c85937e13c51641ef71  data/loc/3314493806_6f1db86d66_o_d.jpg",
            manifest_txt,
        )
        self.assertIn(
            "e592194b3733e25166a631e1ec55bac08066cbc1  data/si/2584174182_ffd5c24905_b_d.jpg",
            manifest_txt,
        )
        self.assertIn(
            "db49ef009f85a5d0701829f38d29f8cf9c5df2ea  data/si/4011399822_65987a4806_b_d.jpg",
            manifest_txt,
        )

    def test_make_bag_sha256_manifest(self):
        bagit.make_bag(self.tmpdir, checksum=["sha256"])
        # check manifest
        self.assertTrue(os.path.isfile(j(self.tmpdir, "manifest-sha256.txt")))
        manifest_txt = slurp_text_file(
            j(self.tmpdir, "manifest-sha256.txt")
        ).splitlines()
        self.assertIn(
            "b6df8058fa818acfd91759edffa27e473f2308d5a6fca1e07a79189b95879953  data/loc/2478433644_2839c5e8b8_o_d.jpg",
            manifest_txt,
        )
        self.assertIn(
            "1af90c21e72bb0575ae63877b3c69cfb88284f6e8c7820f2c48dc40a08569da5  data/loc/3314493806_6f1db86d66_o_d.jpg",
            manifest_txt,
        )
        self.assertIn(
            "f065a4ae2bc5d47c6d046c3cba5c8cdfd66b07c96ff3604164e2c31328e41c1a  data/si/2584174182_ffd5c24905_b_d.jpg",
            manifest_txt,
        )
        self.assertIn(
            "45d257c93e59ec35187c6a34c8e62e72c3e9cfbb548984d6f6e8deb84bac41f4  data/si/4011399822_65987a4806_b_d.jpg",
            manifest_txt,
        )

    def test_make_bag_sha512_manifest(self):
        bagit.make_bag(self.tmpdir, checksum=["sha512"])
        # check manifest
        self.assertTrue(os.path.isfile(j(self.tmpdir, "manifest-sha512.txt")))
        manifest_txt = slurp_text_file(
            j(self.tmpdir, "manifest-sha512.txt")
        ).splitlines()
        self.assertIn(
            "51fb9236a23795886cf42d539d580739245dc08f72c3748b60ed8803c9cb0e2accdb91b75dbe7d94a0a461827929d720ef45fe80b825941862fcde4c546a376d  data/loc/2478433644_2839c5e8b8_o_d.jpg",
            manifest_txt,
        )
        self.assertIn(
            "627c15be7f9aabc395c8b2e4c3ff0b50fd84b3c217ca38044cde50fd4749621e43e63828201fa66a97975e316033e4748fb7a4a500183b571ecf17715ec3aea3  data/loc/3314493806_6f1db86d66_o_d.jpg",
            manifest_txt,
        )
        self.assertIn(
            "4cb4dafe39b2539536a9cb31d5addf335734cb91e2d2786d212a9b574e094d7619a84ad53f82bd9421478a7994cf9d3f44fea271d542af09d26ce764edbada46  data/si/2584174182_ffd5c24905_b_d.jpg",
            manifest_txt,
        )
        self.assertIn(
            "af1c03483cd1999098cce5f9e7689eea1f81899587508f59ba3c582d376f8bad34e75fed55fd1b1c26bd0c7a06671b85e90af99abac8753ad3d76d8d6bb31ebd  data/si/4011399822_65987a4806_b_d.jpg",
            manifest_txt,
        )

    def test_make_bag_unknown_algorithm(self):
        self.assertRaises(
            ValueError, bagit.make_bag, self.tmpdir, checksum=["not-really-a-name"]
        )

    def test_make_bag_with_empty_directory(self):
        tmpdir = tempfile.mkdtemp()
        try:
            bagit.make_bag(tmpdir)
        finally:
            shutil.rmtree(tmpdir)

    def test_make_bag_with_empty_directory_tree(self):
        tmpdir = tempfile.mkdtemp()
        path = j(tmpdir, "test1", "test2")
        try:
            os.makedirs(path)
            bagit.make_bag(tmpdir)
        finally:
            shutil.rmtree(tmpdir)

    def test_make_bag_with_bogus_directory(self):
        bogus_directory = os.path.realpath("this-directory-does-not-exist")

        with self.assertRaises(RuntimeError) as error_catcher:
            bagit.make_bag(bogus_directory)

        self.assertEqual(
            "Bag directory %s does not exist" % bogus_directory,
            str(error_catcher.exception),
        )

    def test_make_bag_with_unreadable_source(self):
        os.chmod(self.tmpdir, 0)

        with self.assertRaises(bagit.BagError) as error_catcher:
            bagit.make_bag(self.tmpdir, checksum=["sha256"])

        self.assertEqual(
            "Missing permissions to move all files and directories",
            str(error_catcher.exception),
        )

    def test_make_bag_with_unreadable_subdirectory(self):
        # We'll set this write-only to exercise the second permission check in make_bag:
        os.chmod(j(self.tmpdir, "loc"), 0o200)

        with self.assertRaises(bagit.BagError) as error_catcher:
            bagit.make_bag(self.tmpdir, checksum=["sha256"])

        self.assertEqual(
            "Read permissions are required to calculate file fixities",
            str(error_catcher.exception),
        )

    def test_make_bag_with_unwritable_source(self):
        path_suffixes = ("", "loc")

        for path_suffix in reversed(path_suffixes):
            os.chmod(j(self.tmpdir, path_suffix), 0o500)

        with self.assertRaises(bagit.BagError) as error_catcher:
            bagit.make_bag(self.tmpdir, checksum=["sha256"])

        self.assertEqual(
            "Missing permissions to move all files and directories",
            str(error_catcher.exception),
        )

    def test_make_bag_with_unreadable_file(self):
        os.chmod(j(self.tmpdir, "loc", "2478433644_2839c5e8b8_o_d.jpg"), 0)

        with self.assertRaises(bagit.BagError) as error_catcher:
            bagit.make_bag(self.tmpdir, checksum=["sha256"])

        self.assertEqual(
            "Read permissions are required to calculate file fixities",
            str(error_catcher.exception),
        )

    def test_make_bag_with_data_dir_present(self):
        os.mkdir(j(self.tmpdir, "data"))
        bagit.make_bag(self.tmpdir)

        # data dir should now contain another data dir
        self.assertTrue(os.path.isdir(j(self.tmpdir, "data", "data")))

    def test_bag_class(self):
        info = {"Contact-Email": "ehs@pobox.com"}
        bag = bagit.make_bag(self.tmpdir, bag_info=info, checksums=["sha384"])
        self.assertIsInstance(bag, bagit.Bag)
        self.assertEqual(
            set(bag.payload_files()),
            set(
                [
                    "data/README",
                    "data/si/2584174182_ffd5c24905_b_d.jpg",
                    "data/si/4011399822_65987a4806_b_d.jpg",
                    "data/loc/2478433644_2839c5e8b8_o_d.jpg",
                    "data/loc/3314493806_6f1db86d66_o_d.jpg",
                ]
            ),
        )
        self.assertEqual(
            list(bag.manifest_files()), ["%s/manifest-sha384.txt" % self.tmpdir]
        )

    def test_bag_string_representation(self):
        bag = bagit.make_bag(self.tmpdir)
        self.assertEqual(self.tmpdir, str(bag))

    def test_has_oxum(self):
        bag = bagit.make_bag(self.tmpdir)
        self.assertTrue(bag.has_oxum())

    def test_bag_constructor(self):
        bag = bagit.make_bag(self.tmpdir)
        bag = bagit.Bag(self.tmpdir)
        self.assertEqual(type(bag), bagit.Bag)
        self.assertEqual(len(list(bag.payload_files())), 5)

    def test_is_valid(self):
        bag = bagit.make_bag(self.tmpdir)
        bag = bagit.Bag(self.tmpdir)
        self.assertTrue(bag.is_valid())
        with open(j(self.tmpdir, "data", "extra_file"), "w") as ef:
            ef.write("bar")
        self.assertFalse(bag.is_valid())

    def test_garbage_in_bagit_txt(self):
        bagit.make_bag(self.tmpdir)
        bagfile = """BagIt-Version: 0.97
Tag-File-Character-Encoding: UTF-8
==================================
"""
        with open(j(self.tmpdir, "bagit.txt"), "w") as bf:
            bf.write(bagfile)
        self.assertRaises(bagit.BagValidationError, bagit.Bag, self.tmpdir)

    def test_make_bag_multiprocessing(self):
        bagit.make_bag(self.tmpdir, processes=2)
        self.assertTrue(os.path.isdir(j(self.tmpdir, "data")))

    def test_multiple_meta_values(self):
        baginfo = {"Multival-Meta": [7, 4, 8, 6, 8]}
        bag = bagit.make_bag(self.tmpdir, baginfo)
        meta = bag.info.get("Multival-Meta")
        self.assertEqual(type(meta), list)
        self.assertEqual(len(meta), len(baginfo["Multival-Meta"]))

    def test_unicode_bag_info(self):
        info = {
            "Test-BMP": "This element contains a \N{LATIN SMALL LETTER U WITH DIAERESIS}",
            "Test-SMP": "This element contains a \N{LINEAR B SYMBOL B049}",
        }

        bagit.make_bag(self.tmpdir, bag_info=info, checksums=["md5"])

        bag_info_txt = slurp_text_file(j(self.tmpdir, "bag-info.txt"))
        for v in info.values():
            self.assertIn(v, bag_info_txt)

    def test_unusual_bag_info_separators(self):
        bag = bagit.make_bag(self.tmpdir)

        with open(j(self.tmpdir, "bag-info.txt"), "a") as f:
            print("Test-Tag: 1", file=f)
            print("Test-Tag:\t2", file=f)
            print("Test-Tag\t: 3", file=f)
            print("Test-Tag\t:\t4", file=f)
            print("Test-Tag\t \t: 5", file=f)
            print("Test-Tag:\t \t 6", file=f)

        bag = bagit.Bag(self.tmpdir)
        bag.save(manifests=True)

        self.assertTrue(bag.is_valid())
        self.assertEqual(bag.info["Test-Tag"], list(map(str, range(1, 7))))

    def test_default_bagging_date(self):
        info = {"Contact-Email": "ehs@pobox.com"}
        bagit.make_bag(self.tmpdir, bag_info=info)
        bag_info_txt = slurp_text_file(j(self.tmpdir, "bag-info.txt"))
        self.assertTrue("Contact-Email: ehs@pobox.com" in bag_info_txt)
        today = datetime.date.strftime(datetime.date.today(), "%Y-%m-%d")
        self.assertTrue("Bagging-Date: %s" % today in bag_info_txt)

    def test_missing_tagmanifest_valid(self):
        info = {"Contact-Email": "ehs@pobox.com"}
        bag = bagit.make_bag(self.tmpdir, bag_info=info, checksums=["md5"])
        self.assertTrue(bag.is_valid())
        os.remove(j(self.tmpdir, "tagmanifest-md5.txt"))
        self.assertTrue(bag.is_valid())

    def test_carriage_return_manifest(self):
        with open(j(self.tmpdir, "newline\r"), "w") as whatever:
            whatever.write("ugh")
        bag = bagit.make_bag(self.tmpdir)
        self.assertTrue(bag.is_valid())

    def test_payload_permissions(self):
        perms = os.stat(self.tmpdir).st_mode

        # our tmpdir should not be writeable by group
        self.assertEqual(perms & stat.S_IWOTH, 0)

        # but if we make it writeable by the group then resulting
        # payload directory should have the same permissions
        new_perms = perms | stat.S_IWOTH
        self.assertTrue(perms != new_perms)
        os.chmod(self.tmpdir, new_perms)
        bagit.make_bag(self.tmpdir)
        payload_dir = j(self.tmpdir, "data")
        self.assertEqual(os.stat(payload_dir).st_mode, new_perms)

    def test_save_bag_to_unwritable_directory(self):
        bag = bagit.make_bag(self.tmpdir, checksum=["sha256"])

        os.chmod(self.tmpdir, 0)

        with self.assertRaises(bagit.BagError) as error_catcher:
            bag.save()

        self.assertEqual(
            "Cannot save bag to non-existent or inaccessible directory %s"
            % self.tmpdir,
            str(error_catcher.exception),
        )

    def test_save_bag_with_unwritable_file(self):
        bag = bagit.make_bag(self.tmpdir, checksum=["sha256"])

        os.chmod(os.path.join(self.tmpdir, "bag-info.txt"), 0)

        with self.assertRaises(bagit.BagError) as error_catcher:
            bag.save()

        self.assertEqual(
            "Read permissions are required to calculate file fixities",
            str(error_catcher.exception),
        )

    def test_save_manifests(self):
        bag = bagit.make_bag(self.tmpdir)
        self.assertTrue(bag.is_valid())
        bag.save(manifests=True)
        self.assertTrue(bag.is_valid())
        with open(j(self.tmpdir, "data", "newfile"), "w") as nf:
            nf.write("newfile")
        self.assertRaises(bagit.BagValidationError, bag.validate, bag, fast=False)
        bag.save(manifests=True)
        self.assertTrue(bag.is_valid())

    def test_save_manifests_deleted_files(self):
        bag = bagit.make_bag(self.tmpdir)
        self.assertTrue(bag.is_valid())
        bag.save(manifests=True)
        self.assertTrue(bag.is_valid())
        os.remove(j(self.tmpdir, "data", "loc", "2478433644_2839c5e8b8_o_d.jpg"))
        self.assertRaises(bagit.BagValidationError, bag.validate, bag, fast=False)
        bag.save(manifests=True)
        self.assertTrue(bag.is_valid())

    def test_save_baginfo(self):
        bag = bagit.make_bag(self.tmpdir)

        bag.info["foo"] = "bar"
        bag.save()
        bag = bagit.Bag(self.tmpdir)
        self.assertEqual(bag.info["foo"], "bar")
        self.assertTrue(bag.is_valid())

        bag.info["x"] = ["a", "b", "c"]
        bag.save()
        b = bagit.Bag(self.tmpdir)
        self.assertEqual(b.info["x"], ["a", "b", "c"])
        self.assertTrue(bag.is_valid())

    def test_save_baginfo_with_sha1(self):
        bag = bagit.make_bag(self.tmpdir, checksum=["sha1", "md5"])
        self.assertTrue(bag.is_valid())
        bag.save()

        bag.info["foo"] = "bar"
        bag.save()

        bag = bagit.Bag(self.tmpdir)
        self.assertTrue(bag.is_valid())

    def test_save_only_baginfo(self):
        bag = bagit.make_bag(self.tmpdir)
        with open(j(self.tmpdir, "data", "newfile"), "w") as nf:
            nf.write("newfile")
        bag.info["foo"] = "bar"
        bag.save()

        bag = bagit.Bag(self.tmpdir)
        self.assertEqual(bag.info["foo"], "bar")
        self.assertFalse(bag.is_valid())

    def test_make_bag_with_newline(self):
        bag = bagit.make_bag(self.tmpdir, {"test": "foo\nbar"})
        self.assertEqual(bag.info["test"], "foobar")

    def test_unicode_in_tags(self):
        bag = bagit.make_bag(self.tmpdir, {"test": "♡"})
        bag = bagit.Bag(self.tmpdir)
        self.assertEqual(bag.info["test"], "♡")

    def test_filename_unicode_normalization(self):
        # We need to handle cases where the Unicode normalization form of a
        # filename has changed in-transit. This is hard to do portably in both
        # directions because OS X normalizes *all* filenames to an NFD variant
        # so we'll start with a basic test which writes the manifest using the
        # NFC form and confirm that this does not cause the bag to fail when it
        # is written to the filesystem using the NFD form, which will not be
        # altered when saved to an HFS+ filesystem:

        test_filename = "Núñez Papers.txt"
        test_filename_nfd = unicodedata.normalize("NFD", test_filename)

        os.makedirs(j(self.tmpdir, "unicode-normalization"))

        with open(j(self.tmpdir, "unicode-normalization", test_filename_nfd), "w") as f:
            f.write("This is a test filename written using NFD normalization\n")

        bag = bagit.make_bag(self.tmpdir)
        bag.save()

        self.assertTrue(bag.is_valid())

        # Now we'll cause the entire manifest file was normalized to NFC:
        for m_f in bag.manifest_files():
            contents = slurp_text_file(m_f)
            normalized_bytes = unicodedata.normalize("NFC", contents).encode("utf-8")
            with open(m_f, "wb") as f:
                f.write(normalized_bytes)

        for alg in bag.algorithms:
            bagit._make_tagmanifest_file(alg, bag.path, encoding=bag.encoding)

        # Now we'll reload the whole thing:
        bag = bagit.Bag(self.tmpdir)
        self.assertTrue(bag.is_valid())

    def test_open_bag_with_missing_bagit_txt(self):
        bagit.make_bag(self.tmpdir)

        os.unlink(j(self.tmpdir, "bagit.txt"))

        with self.assertRaises(bagit.BagError) as error_catcher:
            bagit.Bag(self.tmpdir)

        self.assertEqual(
            "Expected bagit.txt does not exist: %s/bagit.txt" % self.tmpdir,
            str(error_catcher.exception),
        )

    def test_open_bag_with_malformed_bagit_txt(self):
        bagit.make_bag(self.tmpdir)

        with open(j(self.tmpdir, "bagit.txt"), "w") as f:
            os.ftruncate(f.fileno(), 0)

        with self.assertRaises(bagit.BagError) as error_catcher:
            bagit.Bag(self.tmpdir)

        self.assertEqual(
            "Missing required tag in bagit.txt: BagIt-Version, Tag-File-Character-Encoding",
            str(error_catcher.exception),
        )

    def test_open_bag_with_invalid_versions(self):
        bagit.make_bag(self.tmpdir)

        for v in ("a.b", "2.", "0.1.2", "1.2.3"):
            with open(j(self.tmpdir, "bagit.txt"), "w") as f:
                f.write("BagIt-Version: %s\nTag-File-Character-Encoding: UTF-8\n" % v)

            with self.assertRaises(bagit.BagError) as error_catcher:
                bagit.Bag(self.tmpdir)

            self.assertEqual(
                "Bag version numbers must be MAJOR.MINOR numbers, not %s" % v,
                str(error_catcher.exception),
            )

    def test_open_bag_with_unsupported_version(self):
        bagit.make_bag(self.tmpdir)

        with open(j(self.tmpdir, "bagit.txt"), "w") as f:
            f.write("BagIt-Version: 2.0\nTag-File-Character-Encoding: UTF-8\n")

        with self.assertRaises(bagit.BagError) as error_catcher:
            bagit.Bag(self.tmpdir)

        self.assertEqual("Unsupported bag version: 2.0", str(error_catcher.exception))

    def test_open_bag_with_unknown_encoding(self):
        bagit.make_bag(self.tmpdir)

        with open(j(self.tmpdir, "bagit.txt"), "w") as f:
            f.write("BagIt-Version: 0.97\nTag-File-Character-Encoding: WTF-8\n")

        with self.assertRaises(bagit.BagError) as error_catcher:
            bagit.Bag(self.tmpdir)

        self.assertEqual("Unsupported encoding: WTF-8", str(error_catcher.exception))


class TestFetch(SelfCleaningTestCase):
    def setUp(self):
        super(TestFetch, self).setUp()

        # All of these tests will involve fetch.txt usage with an existing bag
        # so we'll simply create one:
        self.bag = bagit.make_bag(self.tmpdir)

    def test_fetch_loader(self):
        with open(j(self.tmpdir, "fetch.txt"), "w") as fetch_txt:
            print(
                "https://photojournal.jpl.nasa.gov/jpeg/PIA21390.jpg - data/nasa/PIA21390.jpg",
                file=fetch_txt,
            )

        self.bag.save(manifests=True)
        self.bag.validate()

        self.assertListEqual(
            [
                (
                    "https://photojournal.jpl.nasa.gov/jpeg/PIA21390.jpg",
                    "-",
                    "data/nasa/PIA21390.jpg",
                )
            ],
            list(self.bag.fetch_entries()),
        )

        self.assertListEqual(
            ["data/nasa/PIA21390.jpg"], list(self.bag.files_to_be_fetched())
        )

        self.assertListEqual(
            ["data/nasa/PIA21390.jpg"], list(self.bag.compare_fetch_with_fs())
        )

    def test_fetch_validation(self):
        with open(j(self.tmpdir, "fetch.txt"), "w") as fetch_txt:
            print(
                "https://photojournal.jpl.nasa.gov/jpeg/PIA21390.jpg - data/nasa/PIA21390.jpg",
                file=fetch_txt,
            )

        self.bag.save(manifests=True)

        with mock.patch.object(bagit.Bag, "validate_fetch") as mock_vf:
            self.bag.validate()
            self.assertTrue(
                mock_vf.called, msg="Bag.validate() should call Bag.validate_fetch()"
            )

    def test_fetch_unsafe_payloads(self):
        with open(j(self.tmpdir, "fetch.txt"), "w") as fetch_txt:
            print(
                "https://photojournal.jpl.nasa.gov/jpeg/PIA21390.jpg - /etc/passwd",
                file=fetch_txt,
            )

        self.bag.save(manifests=True)

        expected_msg = 'Path "/etc/passwd" in "%s/fetch.txt" is unsafe' % self.tmpdir

        # We expect both validate() and fetch entry iteration to raise errors on security hazards
        # so we'll test both:

        with self.assertRaises(bagit.BagError) as cm:
            self.bag.validate()

        self.assertEqual(expected_msg, str(cm.exception))

        # Note the use of list() to exhaust the fetch_entries generator:
        with self.assertRaises(bagit.BagError) as cm:
            list(self.bag.fetch_entries())

        self.assertEqual(expected_msg, str(cm.exception))

    def test_fetch_malformed_url(self):
        with open(j(self.tmpdir, "fetch.txt"), "w") as fetch_txt:
            print(
                "//photojournal.jpl.nasa.gov/jpeg/PIA21390.jpg - data/nasa/PIA21390.jpg",
                file=fetch_txt,
            )

        self.bag.save(manifests=True)

        expected_msg = (
            "Malformed URL in fetch.txt: //photojournal.jpl.nasa.gov/jpeg/PIA21390.jpg"
        )

        with self.assertRaises(bagit.BagError) as cm:
            self.bag.validate_fetch()

        self.assertEqual(expected_msg, str(cm.exception))


class TestUtils(unittest.TestCase):
    def setUp(self):
        super(TestUtils, self).setUp()
        if sys.version_info >= (3,):
            self.unicode_class = str
        else:
            self.unicode_class = unicode

    def test_force_unicode_str_to_unicode(self):
        self.assertIsInstance(bagit.force_unicode("foobar"), self.unicode_class)

    def test_force_unicode_pass_through(self):
        self.assertIsInstance(bagit.force_unicode("foobar"), self.unicode_class)

    def test_force_unicode_int(self):
        self.assertIsInstance(bagit.force_unicode(1234), self.unicode_class)


if __name__ == "__main__":
    unittest.main()

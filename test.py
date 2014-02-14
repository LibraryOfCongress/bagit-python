import os
import shutil
import logging
import datetime
import tempfile
import unittest
import codecs
import hashlib

from os.path import join as j

import bagit

# don't let < ERROR clutter up test output
logging.basicConfig(level=logging.ERROR)


class TestBag(unittest.TestCase):

    def setUp(self):
	self.tmpdir = tempfile.mkdtemp()
	if os.path.isdir(self.tmpdir):
	    shutil.rmtree(self.tmpdir)
        shutil.copytree('test-data', self.tmpdir)

    def tearDown(self):
        if os.path.isdir(self.tmpdir):
            shutil.rmtree(self.tmpdir)

    def test_make_bag(self):
        info = {'Bagging-Date': '1970-01-01', 'Contact-Email': 'ehs@pobox.com'}
        bag = bagit.make_bag(self.tmpdir, bag_info=info)

        # data dir should've been created
        self.assertTrue(os.path.isdir(j(self.tmpdir, 'data')))

        # check bagit.txt
        self.assertTrue(os.path.isfile(j(self.tmpdir, 'bagit.txt')))
        bagit_txt = open(j(self.tmpdir, 'bagit.txt')).read()
        self.assertTrue('BagIt-Version: 0.97' in bagit_txt)
        self.assertTrue('Tag-File-Character-Encoding: UTF-8' in bagit_txt)

        # check manifest
        self.assertTrue(os.path.isfile(j(self.tmpdir, 'manifest-md5.txt')))
        manifest_txt = open(j(self.tmpdir, 'manifest-md5.txt')).read()
        self.assertTrue('8e2af7a0143c7b8f4de0b3fc90f27354  data/README' in manifest_txt)
        self.assertTrue('9a2b89e9940fea6ac3a0cc71b0a933a0  data/loc/2478433644_2839c5e8b8_o_d.jpg' in manifest_txt)
        self.assertTrue('6172e980c2767c12135e3b9d246af5a3  data/loc/3314493806_6f1db86d66_o_d.jpg' in manifest_txt)
        self.assertTrue('38a84cd1c41de793a0bccff6f3ec8ad0  data/si/2584174182_ffd5c24905_b_d.jpg' in manifest_txt)
        self.assertTrue('5580eaa31ad1549739de12df819e9af8  data/si/4011399822_65987a4806_b_d.jpg' in manifest_txt)

        # check bag-info.txt
        self.assertTrue(os.path.isfile(j(self.tmpdir, 'bag-info.txt')))
        bag_info_txt = open(j(self.tmpdir, 'bag-info.txt')).read()
        self.assertTrue('Contact-Email: ehs@pobox.com' in bag_info_txt)
        self.assertTrue('Bagging-Date: 1970-01-01' in bag_info_txt)
        self.assertTrue('Payload-Oxum: 991765.5' in bag_info_txt)
        self.assertTrue('Bag-Software-Agent: bagit.py <http://github.com/libraryofcongress/bagit-python>' in bag_info_txt)

        # check tagmanifest-md5.txt
        self.assertTrue(os.path.isfile(j(self.tmpdir, 'tagmanifest-md5.txt')))
        tagmanifest_txt = open(j(self.tmpdir, 'tagmanifest-md5.txt')).read()
        self.assertTrue('9e5ad981e0d29adc278f6a294b8c2aca bagit.txt' in tagmanifest_txt)
        self.assertTrue('a0ce6631a2a6d1a88e6d38453ccc72a5 manifest-md5.txt' in tagmanifest_txt)
        self.assertTrue('6a5090e27cb29d5dda8a0142fbbdf37e bag-info.txt' in tagmanifest_txt)

    def test_make_bag_with_data_dir_present(self):
        os.mkdir(j(self.tmpdir, 'data'))
        bag = bagit.make_bag(self.tmpdir)

        # data dir should now contain another data dir
        self.assertTrue(os.path.isdir(j(self.tmpdir, 'data', 'data')))

    def test_bag_class(self):
        info = {'Contact-Email': 'ehs@pobox.com'}
        bag = bagit.make_bag(self.tmpdir, bag_info=info)
        self.assertTrue(isinstance(bag, bagit.Bag))
        self.assertEqual(set(bag.payload_files()), set([
            'data/README',
            'data/si/2584174182_ffd5c24905_b_d.jpg',
            'data/si/4011399822_65987a4806_b_d.jpg',
            'data/loc/2478433644_2839c5e8b8_o_d.jpg',
            'data/loc/3314493806_6f1db86d66_o_d.jpg']))
        self.assertEqual(list(bag.manifest_files()), ['%s/manifest-md5.txt' %
            self.tmpdir])

    def test_has_oxum(self):
        bag = bagit.make_bag(self.tmpdir)
        self.assertTrue(bag.has_oxum())

    def test_bag_constructor(self):
        bag = bagit.make_bag(self.tmpdir)
        bag = bagit.Bag(self.tmpdir)
        self.assertEqual(type(bag), bagit.Bag)
        self.assertEqual(len(list(bag.payload_files())), 5)

    def test_validate_flipped_bit(self):
        bag = bagit.make_bag(self.tmpdir)
        readme = os.path.join(self.tmpdir, "data", "README")
        txt = open(readme).read()
        txt = 'A' + txt[1:]
        open(readme, "w").write(txt)
        bag = bagit.Bag(self.tmpdir)
        self.assertRaises(bagit.BagValidationError, bag.validate)
        # fast doesn't catch the flipped bit, since oxsum is the same
        self.assertTrue(bag.validate(fast=True))

    def test_validate_fast(self):
        bag = bagit.make_bag(self.tmpdir)
        self.assertEqual(bag.validate(fast=True), True)
        os.remove(os.path.join(self.tmpdir, "data", "loc",
            "2478433644_2839c5e8b8_o_d.jpg"))
        self.assertRaises(bagit.BagValidationError, bag.validate, fast=True)

    def test_validate_fast_without_oxum(self):
        bag = bagit.make_bag(self.tmpdir)
        os.remove(os.path.join(self.tmpdir, "bag-info.txt"))
        bag = bagit.Bag(self.tmpdir)
        self.assertRaises(bagit.BagValidationError, bag.validate, fast=True)

    def test_validate_slow_without_oxum_extra_file(self):
        bag = bagit.make_bag(self.tmpdir)
        os.remove(os.path.join(self.tmpdir, "bag-info.txt"))
        open(os.path.join(self.tmpdir, "data", "extra_file"), "w").write("foo")
        bag = bagit.Bag(self.tmpdir)
        self.assertRaises(bagit.BagValidationError, bag.validate, fast=False)

    def test_validation_error_details(self):
        bag = bagit.make_bag(self.tmpdir)
        readme = os.path.join(self.tmpdir, "data", "README")
        txt = open(readme).read()
        txt = 'A' + txt[1:]
        open(readme, "w").write(txt)

        extra_file = os.path.join(self.tmpdir, "data", "extra")
        open(extra_file, "w").write('foo')

        # remove the bag-info.txt which contains the oxum to force a full 
        # check of the manifest 
        os.remove(os.path.join(self.tmpdir, "bag-info.txt"))

        bag = bagit.Bag(self.tmpdir)
        got_exception = False
        try:
            bag.validate()
        except bagit.BagValidationError, e:
            got_exception = True

            self.assertEqual(str(e), "invalid bag: bag-info.txt exists in manifest but not found on filesystem ; data/extra exists on filesystem but is not in manifest ; data/README checksum validation failed (alg=md5 expected=8e2af7a0143c7b8f4de0b3fc90f27354 found=fd41543285d17e7c29cd953f5cf5b955)")
            self.assertEqual(len(e.details), 3)

            error = e.details[0]
            self.assertEqual(str(error), "bag-info.txt exists in manifest but not found on filesystem")
            self.assertTrue(isinstance(error, bagit.FileMissing))
            self.assertEqual(error.path, "bag-info.txt")

            error = e.details[1]
            self.assertEqual(str(error), "data/extra exists on filesystem but is not in manifest")
            self.assertTrue(isinstance(error, bagit.UnexpectedFile))
            self.assertEqual(error.path, "data/extra")

            error = e.details[2]
            self.assertEqual(str(error), "data/README checksum validation failed (alg=md5 expected=8e2af7a0143c7b8f4de0b3fc90f27354 found=fd41543285d17e7c29cd953f5cf5b955)")
            self.assertTrue(isinstance(error, bagit.ChecksumMismatch))
            self.assertEqual(error.algorithm, 'md5')
            self.assertEqual(error.path, 'data/README')
            self.assertEqual(error.expected, '8e2af7a0143c7b8f4de0b3fc90f27354')
            self.assertEqual(error.found, 'fd41543285d17e7c29cd953f5cf5b955')
        if not got_exception:
            self.fail("didn't get BagValidationError")

    def test_is_valid(self):
        bag = bagit.make_bag(self.tmpdir)
        bag = bagit.Bag(self.tmpdir)
        self.assertTrue(bag.is_valid())
        open(os.path.join(self.tmpdir, "data", "extra_file"), "w").write("bar")
        self.assertFalse(bag.is_valid())

    def test_bom_in_bagit_txt(self):
        bag = bagit.make_bag(self.tmpdir)
        bagfile = codecs.BOM_UTF8
        bagfile += open(os.path.join(self.tmpdir, "bagit.txt"), "rb").read()
        bf = open(os.path.join(self.tmpdir, "bagit.txt"), "wb")
        bf.write(bagfile)
        bf.close()
        bag = bagit.Bag(self.tmpdir)
        self.assertRaises(bagit.BagValidationError, bag.validate)

    def test_missing_file(self):
        bag = bagit.make_bag(self.tmpdir)
        os.remove(j(self.tmpdir, 'data', 'loc', '3314493806_6f1db86d66_o_d.jpg'))
        self.assertRaises(bagit.BagValidationError, bag.validate)

    def test_handle_directory_end_slash_gracefully(self):
        bag = bagit.make_bag(self.tmpdir + '/')
        self.assertTrue(bag.validate())
        bag2 = bagit.Bag(self.tmpdir + '/')
        self.assertTrue(bag2.validate())

    def test_allow_extraneous_files_in_base(self):
        bag = bagit.make_bag(self.tmpdir)
        self.assertTrue(bag.validate())
        f = os.path.join(self.tmpdir, "IGNOREFILE")
        open(f, 'w')
        self.assertTrue(bag.validate())

    def test_allow_extraneous_dirs_in_base(self):
        bag = bagit.make_bag(self.tmpdir)
        self.assertTrue(bag.validate())
        d = os.path.join(self.tmpdir, "IGNOREDIR")
        os.mkdir(d)
        self.assertTrue(bag.validate())

    def test_missing_tagfile_raises_error(self):
        bag = bagit.make_bag(self.tmpdir)
        self.assertTrue(bag.validate())
        os.remove(os.path.join(self.tmpdir, "bagit.txt"))
        self.assertRaises(bagit.BagValidationError, bag.validate)

    def test_missing_manifest_raises_error(self):
        bag = bagit.make_bag(self.tmpdir)
        self.assertTrue(bag.validate())
        os.remove(os.path.join(self.tmpdir, "manifest-md5.txt"))
        self.assertRaises(bagit.BagValidationError, bag.validate)

    def test_make_bag_multiprocessing(self):
        bag = bagit.make_bag(self.tmpdir, processes=2)
        self.assertTrue(os.path.isdir(j(self.tmpdir, 'data')))

    def test_mixed_case_checksums(self):
        bag = bagit.make_bag(self.tmpdir)
        hashstr = {}
        #Extract entries only for the payload and ignore
        # entries from the tagmanifest file
        for key in bag.entries.iterkeys():
            if key.startswith('data' + os.sep):
                hashstr = bag.entries[key]
        hashstr = hashstr.itervalues().next()
        manifest = open(os.path.join(self.tmpdir, "manifest-md5.txt"),
                        "r").read()
        manifest = manifest.replace(hashstr, hashstr.upper())
        open(os.path.join(self.tmpdir, "manifest-md5.txt"),
             "w").write(manifest)

        #Since manifest-md5.txt file is updated, re-calculate its
        # md5 checksum and update it in the tagmanifest-md5.txt file
        hasher = hashlib.new('md5')
        hasher.update(open(os.path.join(self.tmpdir, "manifest-md5.txt"),
                      "r").read())
        tagmanifest = open(os.path.join(self.tmpdir, "tagmanifest-md5.txt"),
                           "r").read()
        tagmanifest = tagmanifest.replace(
            bag.entries['manifest-md5.txt']['md5'], hasher.hexdigest())
        open(os.path.join(self.tmpdir, "tagmanifest-md5.txt"),
             "w").write(tagmanifest)

        bag = bagit.Bag(self.tmpdir)
        self.assertTrue(bag.validate())

    def test_multiple_oxum_values(self):
        bag = bagit.make_bag(self.tmpdir)
        baginfo = open(os.path.join(self.tmpdir, "bag-info.txt"), "a")
        baginfo.write('Payload-Oxum: 7.7\n')
        baginfo.close()
        bag = bagit.Bag(self.tmpdir)
        self.assertTrue(bag.validate(fast=True))

    def test_multiple_meta_values(self):
        baginfo = {"Multival-Meta": [7, 4, 8, 6, 8]}
        bag = bagit.make_bag(self.tmpdir, baginfo)
        meta = bag.info.get("Multival-Meta")
        self.assertEqual(type(meta), list)
        self.assertEqual(len(meta), len(baginfo["Multival-Meta"]))

    def test_validate_optional_tagfile(self):
        bag = bagit.make_bag(self.tmpdir)
        tagdir = tempfile.mkdtemp(dir=self.tmpdir)
        tagfile = open(os.path.join(tagdir, "tagfile"), "w")
        tagfile.write("test")
        tagfile.close()
        relpath = os.path.join(tagdir, "tagfile").replace(self.tmpdir + os.sep, "")
        relpath.replace("\\", "/")
        tagman = open(os.path.join(self.tmpdir, "tagmanifest-md5.txt"), "w")

        # Incorrect checksum.
        tagman.write("8e2af7a0143c7b8f4de0b3fc90f27354 " + relpath + "\n")
        tagman.close()
        bag = bagit.Bag(self.tmpdir)
        self.assertRaises(bagit.BagValidationError, bag.validate)

        hasher = hashlib.new("md5")
        hasher.update(open(os.path.join(tagdir, "tagfile"), "rb").read())
        tagman = open(os.path.join(self.tmpdir, "tagmanifest-md5.txt"), "w")
        tagman.write(hasher.hexdigest() + " " + relpath + "\n")
        tagman.close()
        bag = bagit.Bag(self.tmpdir)
        self.assertTrue(bag.validate())

        # Missing tagfile.
        os.remove(os.path.join(tagdir, "tagfile"))
        bag = bagit.Bag(self.tmpdir)
        self.assertRaises(bagit.BagValidationError, bag.validate)
    
    def test_default_bagging_date(self):
        info = {'Contact-Email': 'ehs@pobox.com'}
        bag = bagit.make_bag(self.tmpdir, bag_info=info)
        bag_info_txt = open(j(self.tmpdir, 'bag-info.txt')).read()
        self.assertTrue('Contact-Email: ehs@pobox.com' in bag_info_txt)
        today = datetime.date.strftime(datetime.date.today(), "%Y-%m-%d")
        self.assertTrue('Bagging-Date: %s' % today in bag_info_txt)



if __name__ == '__main__':
    unittest.main()

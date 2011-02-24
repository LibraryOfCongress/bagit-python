import os
import shutil
import logging
import datetime
import unittest

import bagit

# don't let < ERROR clutter up test output
logging.basicConfig(level=logging.ERROR)


class TestBag(unittest.TestCase):

    def setUp(self):
        if os.path.isdir('test-data-tmp'):
            shutil.rmtree('test-data-tmp')
        shutil.copytree('test-data', 'test-data-tmp')

    def tearDown(self):
        if os.path.isdir('test-data-tmp'):
            shutil.rmtree('test-data-tmp')

    def test_make_bag(self):
        info = {'Contact-Email': 'ehs@pobox.com'}
        bag = bagit.make_bag('test-data-tmp', bag_info=info)

        # data dir should've been created
        self.assertTrue(os.path.isdir('test-data-tmp/data'))

        # check bagit.txt
        self.assertTrue(os.path.isfile('test-data-tmp/bagit.txt'))
        bagit_txt = open('test-data-tmp/bagit.txt').read()
        self.assertTrue('BagIt-Version: 0.96' in bagit_txt)
        self.assertTrue('Tag-File-Character-Encoding: UTF-8' in bagit_txt)

        # check manifest
        self.assertTrue(os.path.isfile('test-data-tmp/manifest-md5.txt'))
        manifest_txt = open('test-data-tmp/manifest-md5.txt').read()
        self.assertTrue('8e2af7a0143c7b8f4de0b3fc90f27354  data/README' in manifest_txt)
        self.assertTrue('9a2b89e9940fea6ac3a0cc71b0a933a0  data/loc/2478433644_2839c5e8b8_o_d.jpg' in manifest_txt)
        self.assertTrue('6172e980c2767c12135e3b9d246af5a3  data/loc/3314493806_6f1db86d66_o_d.jpg' in manifest_txt)
        self.assertTrue('38a84cd1c41de793a0bccff6f3ec8ad0  data/si/2584174182_ffd5c24905_b_d.jpg' in manifest_txt)
        self.assertTrue('5580eaa31ad1549739de12df819e9af8  data/si/4011399822_65987a4806_b_d.jpg' in manifest_txt)

        # check bag-info.txt
        self.assertTrue(os.path.isfile('test-data-tmp/bag-info.txt'))
        bag_info_txt = open('test-data-tmp/bag-info.txt').read()
        self.assertTrue('Contact-Email: ehs@pobox.com' in bag_info_txt)
        today = datetime.date.strftime(datetime.date.today(), "%Y-%m-%d")
        self.assertTrue('Bagging-Date: %s' % today in bag_info_txt)
        self.assertTrue('Payload-Oxum: 991765.5' in bag_info_txt)

    def test_bag_class(self):
        info = {'Contact-Email': 'ehs@pobox.com'}
        bag = bagit.make_bag('test-data-tmp', bag_info=info)
        self.assertTrue(isinstance(bag, bagit.Bag))
        self.assertEqual(set(bag.payload_files()), set([
            'data/README',
            'data/si/2584174182_ffd5c24905_b_d.jpg',
            'data/si/4011399822_65987a4806_b_d.jpg',
            'data/loc/2478433644_2839c5e8b8_o_d.jpg',
            'data/loc/3314493806_6f1db86d66_o_d.jpg']))
        self.assertEqual(list(bag.manifest_files()), ['test-data-tmp/manifest-md5.txt'])

    def test_has_oxum(self):
        bag = bagit.make_bag('test-data-tmp')
        self.assertTrue(bag.has_oxum())

    def test_bag_constructor(self):
        bag = bagit.make_bag('test-data-tmp')
        bag = bagit.Bag('test-data-tmp')
        self.assertEqual(type(bag), bagit.Bag)
        self.assertEqual(len(list(bag.payload_files())), 5)

    def test_bag_url(self):
        bag = bagit.Bag('http://chroniclingamerica.loc.gov/data/dlc/batch_dlc_jamaica_ver01/')
        self.assertEqual(len(bag.entries), 19396)

    def test_validate(self):
        bag = bagit.make_bag('test-data-tmp')
        self.assertEqual(bag.validate(), True)
        os.remove(os.path.join("test-data-tmp", "data", "loc",
            "2478433644_2839c5e8b8_o_d.jpg"))
        self.assertRaises(bagit.BagValidationError, bag.validate)

    def test_validate_flipped_bit(self):
        bag = bagit.make_bag('test-data-tmp')
        readme = os.path.join("test-data-tmp", "data", "README")
        txt = open(readme).read()
        txt = 'A' + txt[1:]
        open(readme, "w").write(txt)
        bag = bagit.Bag('test-data-tmp')
        self.assertRaises(bagit.BagValidationError, bag.validate)
        # fast doesn't catch the flipped bit, since oxsum is the same
        self.assertTrue(bag.validate(fast=True))

    def test_validate_fast(self):
        bag = bagit.make_bag('test-data-tmp')
        self.assertEqual(bag.validate(fast=True), True)
        os.remove(os.path.join("test-data-tmp", "data", "loc",
            "2478433644_2839c5e8b8_o_d.jpg"))
        self.assertRaises(bagit.BagValidationError, bag.validate, fast=True)

    def test_validate_fast_without_oxum(self):
        bag = bagit.make_bag('test-data-tmp')
        os.remove(os.path.join("test-data-tmp", "bag-info.txt"))
        bag = bagit.Bag('test-data-tmp')
        self.assertRaises(bagit.BagValidationError, bag.validate, fast=True)

    def test_missing_file(self):
        bag = bagit.make_bag('test-data-tmp')
        os.remove('test-data-tmp/data/loc/3314493806_6f1db86d66_o_d.jpg')
        self.assertRaises(bagit.BagValidationError, bag.validate)

    def test_handle_directory_end_slash_gracefully(self):
        bag = bagit.make_bag('test-data-tmp/')
        self.assertTrue(bag.validate())
        bag2 = bagit.Bag('test-data-tmp/')
        self.assertTrue(bag2.validate())

    def test_allow_extraneous_files_in_base(self):
        bag = bagit.make_bag('test-data-tmp')
        self.assertTrue(bag.validate())
        f = os.path.join("test-data-tmp", "IGNOREFILE")
        open(f, 'w')
        self.assertTrue(bag.validate())

    def test_allow_extraneous_dirs_in_base(self):
        bag = bagit.make_bag('test-data-tmp')
        self.assertTrue(bag.validate())
        d = os.path.join("test-data-tmp", "IGNOREDIR")
        os.mkdir(d)
        self.assertTrue(bag.validate())

    def test_missing_tagfile_raises_error(self):
        bag = bagit.make_bag('test-data-tmp')
        self.assertTrue(bag.validate())
        os.remove(os.path.join("test-data-tmp", "bagit.txt"))
        self.assertRaises(bagit.BagValidationError, bag.validate)

    def test_missing_manifest_raises_error(self):
        bag = bagit.make_bag('test-data-tmp')
        self.assertTrue(bag.validate())
        os.remove(os.path.join("test-data-tmp", "manifest-md5.txt"))
        self.assertRaises(bagit.BagValidationError, bag.validate)


if __name__ == '__main__':
    unittest.main()

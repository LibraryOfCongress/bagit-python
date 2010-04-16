import os
import sys
import shutil
import datetime
import unittest

import bagit

class TestBag(unittest.TestCase):

    def setUp(self):
        if os.path.isdir('test-data-tmp'):
            shutil.rmtree('test-data-tmp')
        shutil.copytree('test-data', 'test-data-tmp')

    def test_make_bag(self):
        info = {'Contact-Email': 'ehs@pobox.com'}
        bagit.make_bag('test-data-tmp', bag_info=info)

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

    def tearDown(self):
        if os.path.isdir('test-data-tmp'):
            shutil.rmtree('test-data-tmp')

if __name__ == '__main__':
    unittest.main()

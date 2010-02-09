import os
import sys
import shutil
import unittest

import bag

class TestBag(unittest.TestCase):

    def setUp(self):
        if os.path.isdir('test-data-tmp'):
            shutil.rmtree('test-data-tmp')
        shutil.copytree('test-data', 'test-data-tmp')

    def test_make_bag(self):
        bag.make_bag('test-data-tmp')

    def tearDown(self):
        if os.path.isdir('test-data-tmp'):
            shutil.rmtree('test-data-tmp')

if __name__ == '__main__':
    unittest.main()

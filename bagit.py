#!/usr/bin/env python

import os
import logging

from datetime import date

def make_bag(bag_dir, bag_info=None):
    if not os.path.isdir(bag_dir):
        raise RuntimeError("no such bag directory %s" % bag_dir)

    old_dir = os.path.abspath(os.path.curdir)
    os.chdir(bag_dir)

    try:
        logging.info("creating data dir")
        os.system('mkdir data')
        os.system('mv * data 2>/dev/null')

        logging.info("writing manifest-md5.txt")
        os.system('md5deep -rl data > manifest-md5.txt')

        logging.info("writing bagit.txt")
        txt = """BagIt-Version: 0.96\nTag-File-Character-Encoding: UTF-8"""
        open("bagit.txt", "w").write(txt)

        logging.info("writing bag-info.txt")
        bag_info_txt = open("bag-info.txt", "w")
        if bag_info == None:
            bag_info = {}
        bag_info['Bagging-Date'] = date.strftime(date.today(), "%Y-%m-%d")
        headers = bag_info.keys()
        headers.sort()
        for h in headers:
            bag_info_txt.write("%s: %s\n"  % (h, bag_info[h]))
        bag_info_txt.close()

    except Exception, e:
        logging.error(e)

    finally:
        os.chdir(old_dir)

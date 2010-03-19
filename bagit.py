#!/usr/bin/env python

import os
import hashlib
import logging
import multiprocessing

from datetime import date

def make_bag(bag_dir, bag_info=None, processes=1):
    """
    Convert a given directory into a bag. You can pass in arbitrary 
    key/value pairs to put into the bag-info.txt metadata file as 
    the bag_info dictionary.
    """
    logging.info("creating bag for directory %s" % bag_dir)

    if not os.path.isdir(bag_dir):
        logging.error("no such bag directory %s" % bag_dir)
        raise RuntimeError("no such bag directory %s" % bag_dir)

    old_dir = os.path.abspath(os.path.curdir)
    os.chdir(bag_dir)

    try:
        logging.info("creating data dir")
        os.system('mkdir data')
        os.system('mv * data 2>/dev/null')

        logging.info("writing manifest-md5.txt")
        _make_manifest('manifest-md5.txt', 'data', processes)

        logging.info("writing bagit.txt")
        txt = """BagIt-Version: 0.96\nTag-File-Character-Encoding: UTF-8\n"""
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

def _make_manifest(manifest_file, data_dir, processes):
    logging.info('writing manifest with %s processes' % processes)
    pool = multiprocessing.Pool(processes=processes)
    manifest = open(manifest_file, 'w')
    for line in pool.map(_manifest_line, _walk(data_dir)):
        manifest.write(line)
    manifest.close()

def _walk(data_dir):
    for dirpath, dirnames, filenames in os.walk(data_dir):
        for fn in filenames:
            yield os.path.join(dirpath, fn)

def _manifest_line(filename):
    fh = open(filename)
    m = hashlib.md5()
    while True:
        bytes = fh.read(16384)
        if not bytes: break
        m.update(bytes)
    fh.close()
    return "%s  %s\n" % (m.hexdigest(), filename)

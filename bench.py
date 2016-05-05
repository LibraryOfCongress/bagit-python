#!/usr/bin/env python

"""
This is a little benchmarking script to exercise bagit.make_bag and
bagit.validate using 1-8 parallel processes. It will download some images 
from NASA for use in bagging the first time it is run.
"""

import ftplib
import os
import shutil
import timeit

import bagit

# fetch some images from NASA to bag up

if not os.path.isdir('bench-data'):
    print("fetching some images to bag up from nasa")
    os.mkdir('bench-data')
    ftp = ftplib.FTP('nssdcftp.gsfc.nasa.gov')
    ftp.login()

    ftp.cwd('/pub/misc/photo_gallery/hi-res/planetary/mars/')
    files = []
    ftp.retrlines('NLST', files.append)

    for file in files:
        print(("fetching %s" % file))
        fh = open(os.path.join('bench-data', file), 'wb')
        ftp.retrbinary('RETR %s' % file, fh.write)
        fh.close()


# create bags using 1-8 processes

statement = """
import os
import bagit

if os.path.isdir('bench-data/data'):
    os.system("rm bench-data/bag*")
    os.system("mv bench-data/data/* bench-data/")
    os.system("rmdir bench-data/data")

bagit.make_bag('bench-data', processes=%s)
"""

for p in range(1, 9):
    t = timeit.Timer(statement % p)
    print(("create w/ %s processes: %.2f seconds " % (p, (10 * t.timeit(number=10) / 10))))


# validate a bag with 1-8 processes

shutil.copytree('bench-data', 'bench-data-bag')
bagit.make_bag('bench-data-bag')

# validate bench-data using n processes
statement = """
import os
import bagit

bag = bagit.Bag('bench-data-bag')
bag.validate(processes=%s)
"""

# try 1-8 parallel processes
for p in range(1, 9):
    t = timeit.Timer(statement % p)
    print(("validate w/ %s processes: %.2f seconds " % (p, (10 * t.timeit(number=10) / 10))))

shutil.rmtree('bench-data-bag')

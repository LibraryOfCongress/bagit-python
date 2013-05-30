#!/usr/bin/env python

"""
This is a little benchmarking script to exercise bagit.make_bag
using 1-8 parallel processes. It will download some images from
NASA for use in bagging the first time it is run.
"""

import os
import ftplib
import timeit

# fetch some images from NASA to bag up
if not os.path.isdir('bench-data'):
    print("fetching some images to bag up from nasa")
    os.mkdir('bench-data')
    ftp = ftplib.FTP('nssdcftp.gsfc.nasa.gov')
    ftp.login()

    ftp.cwd('/photo_gallery/hi-res/planetary/mars/')
    files = []
    ftp.retrlines('NLST', files.append)

    for file in files:
        print("fetching {0}".format(file))
        fh = open(os.path.join('bench-data', file), 'wb')
        ftp.retrbinary('RETR {0}'.format(file), fh.write)
        fh.close()

# bag up bench-data using n processes
statement = """
import os
import bagit

if os.path.isdir('bench-data/data'):
    os.system("rm bench-data/bag*")
    os.system("mv bench-data/data/* bench-data/")
    os.system("rmdir bench-data/data")

bagit.make_bag('bench-data', processes={0})
"""

# try 1-8 parallel processes
for p in range(1, 9):
    t = timeit.Timer(statement.format(p))
    print("{0} processes: {1:.2f} seconds ".format(p, (10 * t.timeit(number=10) / 10)))

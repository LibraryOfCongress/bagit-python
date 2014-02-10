bagit-python
============

[![Build Status](https://secure.travis-ci.org/LibraryOfCongress/bagit-python.png)](http://travis-ci.org/LibraryOfCongress/bagit-python)

bagit is a Python library and command line utility for working with  [BagIt](http://purl.org/net/bagit) style packages.

Installation
------------

bagit.py is a single-file python module that you can drop into your project as 
needed or you can install globally with:

    pip install bagit

Python v2.4+ is required.

Command Line Usage
------------------

When you install bagit you should get a command line program called bagit.py
which you can use to turn an existing directory into a bag:

    bagit.py --contact-name 'John Kunze' /directory/to/bag

You can pass in key/value metadata for the bag using options like 
`--contact-name` above, which get persisted to the bag-info.txt. For a 
complete list of bag-info.txt properties you can use as commmand line
arguments see `--help`.

Since calculating checksums can take a while when creating a bag, you may want 
to calculate them in parallel if you are on a multicore machine. You can do 
that with the `--processes` option:

    bagit.py --processes 4 /directory/to/bag

If you would like to validate a bag you can use the --validate flag.

    bagit.py --validate /path/to/bag

If you would like to take a quick look at the bag to see if it seems valid
by just examining the structure of the bag, and comparing its payload-oxum (byte
count and number of files) then use the `--fast` flag.

    bagit.py --validate --fast /path/to/bag

Python Usage
------------

You can also use bagit programatically in your own Python programs. To 
create a bag you would do this:

```python
import bagit
bag = bagit.make_bag('mydir', {'Contact-Name': 'John Kunze'})
```

`make_bag` returns a Bag instance. If you have a bag already on disk and would
like to create a Bag instance for it, simply call the constructor directly:

```python
import bagit
bag = bagit.Bag('/path/to/bag')
```

If you would like to see if a bag is valid, use its `is_valid` method:

```python
bag = bagit.Bag('/path/to/bag')
if bag.is_valid():
    print "yay :)"
else:
    print "boo :("
```

If you'd like to get a detailed list of validation errors, 
execute the `validate` method and catch the `BagValidationError` 
exception. If the bag's manifest was invalid (and it wasn't caught by the 
payload oxum) the exception's `details` property will contain a list of 
`ManifestError`s that you can introspect on. Each ManifestError, will be of 
type `ChecksumMismatch`, `FileMissing`, `UnexpectedFile`.

So for example if you want to print out checksums that failed to validate 
you can do this:

```python

import bagit

bag = bagit.Bag("/path/to/bag")

try:
  bag.validate()

except bagit.BagValidationError, e:
  for d in e.details:
    if isinstance(d, bag.ChecksumMismatch):
      print "expected %s to have %s checksum of %s but found %s" % \
        (e.path, e.algorithm, e.expected, e.found)
```

Development
-----------

    % git clone git://github.com/LibraryOfCongress/bagit-python.git
    % cd bagit-python
    % python test.py

If you'd like to see how increasing parallelization of bag creation on 
your system effects the time to create a bag try using the included bench 
utility:

    % ./bench.py

License
-------

[![cc0](http://i.creativecommons.org/p/zero/1.0/88x31.png)](http://creativecommons.org/publicdomain/zero/1.0/)

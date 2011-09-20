bagit
=====

bagit is a Python library for creating 
[BagIt](http://purl.org/net/bagit) style packages programmatically in Python or from the command line.

Installation
------------

bagit.py is a single-file python module that you can drop into your project as 
needed or you can install globally with:

    easy_install bagit

Usage
-----

From python you can use the bagit module to make a bag like this: 

```python
import bagit
bag = bagit.make_bag('mydir', {'Contact-Name': 'Ed Summers'})
```

Or if you've got an existing bag

```python
import bagit
bag = bagit.Bag('/path/to/bag')
```

Or from the command line:

    bagit.py --contact-name 'Ed Summers' mydir

If you'd like to generate the checksums using parallel system processes, 
instead of single process:

```python
bagit.make_bag('mydir', {'Contact-Name': 'Ed Summers'}, processes=4) 
```

or:

    bagit.py --processes 4 --contact-name 'Ed Summers' mydir

bag --help will give the full set of options.

Development
-----------

    % git clone git://github.com/edsu/bagit.git
    % cd bagit 
    % python test.py

If you'd like to see how increasingl parallelization of bag creation on 
your system effects the time to create a bag try using the included bench 
utility:

    % ./bench.py

License
-------

Public Domain <http://creativecommons.org/licenses/publicdomain/>

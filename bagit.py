#!/usr/bin/env python

"""
BagIt is a directory, filename convention for bundling an arbitrary set of
files with a manifest, checksums, and additional metadata. More about BagIt
can be found at:

    http://purl.org/net/bagit

bagit.py is a pure python drop in library and command line tool for creating,
and working with BagIt directories:

    import bagit
    bag = bagit.make_bag('example-directory', {'Contact-Name': 'Ed Summers'})
    print bag.entries

Basic usage is to give bag a directory to bag up:

    % bagit.py my_directory

You can bag multiple directories if you wish:

    % bagit.py directory1 directory2

Optionally you can pass metadata intended for the bag-info.txt:

    % bagit.py --source-organization "Library of Congress" directory

For more help see:

    % bagit.py --help
"""

import os
import re
import sys
import codecs
import signal
import hashlib
import logging
import optparse
import tempfile
import multiprocessing

from os import listdir
from datetime import date
from os.path import isdir, isfile, join, abspath

logger = logging.getLogger(__name__)

# standard bag-info.txt metadata
_bag_info_headers = [
    'Source-Organization',
    'Organization-Address',
    'Contact-Name',
    'Contact-Phone',
    'Contact-Email',
    'External-Description',
    'External-Identifier',
    'Bag-Size',
    'Bag-Group-Identifier',
    'Bag-Count',
    'Internal-Sender-Identifier',
    'Internal-Sender-Description',
    'BagIt-Profile-Identifier',
    # Bagging-Date is autogenerated
    # Payload-Oxum is autogenerated
]

checksum_algos = ['md5', 'sha1', 'sha256', 'sha512']

BOM = codecs.BOM_UTF8
if sys.version_info[0] >= 3:
    BOM = BOM.decode('utf-8')


def make_bag(bag_dir, bag_info=None, processes=1, checksum=None):
    """
    Convert a given directory into a bag. You can pass in arbitrary
    key/value pairs to put into the bag-info.txt metadata file as
    the bag_info dictionary.
    """
    bag_dir = os.path.abspath(bag_dir)
    logger.info("creating bag for directory %s" % bag_dir)
    # assume md5 checksum if not specified
    if not checksum:
        checksum = ['md5']

    if not os.path.isdir(bag_dir):
        logger.error("no such bag directory %s" % bag_dir)
        raise RuntimeError("no such bag directory %s" % bag_dir)

    old_dir = os.path.abspath(os.path.curdir)
    os.chdir(bag_dir)

    try:
        unbaggable = _can_bag(os.curdir)
        if unbaggable:
            logger.error("no write permissions for the following directories and files: \n%s", unbaggable)
            raise BagError("Not all files/folders can be moved.")
        unreadable_dirs, unreadable_files = _can_read(os.curdir)
        if unreadable_dirs or unreadable_files:
            if unreadable_dirs:
                logger.error("The following directories do not have read permissions: \n%s", unreadable_dirs)
            if unreadable_files:
                logger.error("The following files do not have read permissions: \n%s", unreadable_files)
            raise BagError("Read permissions are required to calculate file fixities.")
        else:
            logger.info("creating data dir")

            cwd = os.getcwd()
            temp_data = tempfile.mkdtemp(dir=cwd)

            for f in os.listdir('.'):
                if os.path.abspath(f) == temp_data:
                    continue
                new_f = os.path.join(temp_data, f)
                logger.info("moving %s to %s" % (f, new_f))
                os.rename(f, new_f)

            logger.info("moving %s to %s" % (temp_data, 'data'))
            os.rename(temp_data, 'data')

            # permissions for the payload directory should match those of the
            # original directory
            os.chmod('data', os.stat(cwd).st_mode)

            for c in checksum:
                logger.info("writing manifest-%s.txt" % c)
                Oxum = _make_manifest('manifest-%s.txt' % c, 'data', processes, c)

            logger.info("writing bagit.txt")
            txt = """BagIt-Version: 0.97\nTag-File-Character-Encoding: UTF-8\n"""
            with open("bagit.txt", "w") as bagit_file:
                bagit_file.write(txt)

            logger.info("writing bag-info.txt")
            if bag_info is None:
                bag_info = {}

            # allow 'Bagging-Date' and 'Bag-Software-Agent' to be overidden
            if 'Bagging-Date' not in bag_info:
                bag_info['Bagging-Date'] = date.strftime(date.today(), "%Y-%m-%d")
            if 'Bag-Software-Agent' not in bag_info:
                bag_info['Bag-Software-Agent'] = 'bagit.py <http://github.com/libraryofcongress/bagit-python>'
            bag_info['Payload-Oxum'] = Oxum
            _make_tag_file('bag-info.txt', bag_info)

            for c in checksum:
                _make_tagmanifest_file(c, bag_dir)
    except Exception:
        logger.exception("An error occurred creating the bag")
        raise
    finally:
        os.chdir(old_dir)

    return Bag(bag_dir)


class Bag(object):
    """A representation of a bag."""

    valid_files = ["bagit.txt", "fetch.txt"]
    valid_directories = ['data']

    def __init__(self, path=None):
        super(Bag, self).__init__()
        self.tags = {}
        self.info = {}
        self.entries = {}
        self.algs = []
        self.tag_file_name = None
        self.path = abspath(path)
        if path:
            # if path ends in a path separator, strip it off
            if path[-1] == os.sep:
                self.path = path[:-1]
            self._open()

    def __str__(self):
        return self.path

    def _open(self):
        # Open the bagit.txt file, and load any tags from it, including
        # the required version and encoding.
        bagit_file_path = os.path.join(self.path, "bagit.txt")

        if not isfile(bagit_file_path):
            raise BagError("No bagit.txt found: %s" % bagit_file_path)

        self.tags = tags = _load_tag_file(bagit_file_path)

        try:
            self.version = tags["BagIt-Version"]
            self.encoding = tags["Tag-File-Character-Encoding"]
        except KeyError as e:
            raise BagError("Missing required tag in bagit.txt: %s" % e)

        if self.version in ["0.93", "0.94", "0.95"]:
            self.tag_file_name = "package-info.txt"
        elif self.version in ["0.96", "0.97"]:
            self.tag_file_name = "bag-info.txt"
        else:
            raise BagError("Unsupported bag version: %s" % self.version)

        if not self.encoding.lower() == "utf-8":
            raise BagValidationError("Unsupported encoding: %s" % self.encoding)

        info_file_path = os.path.join(self.path, self.tag_file_name)
        if os.path.exists(info_file_path):
            self.info = _load_tag_file(info_file_path)

        self._load_manifests()

    def manifest_files(self):
        for filename in ["manifest-%s.txt" % a for a in checksum_algos]:
            f = os.path.join(self.path, filename)
            if isfile(f):
                yield f

    def tagmanifest_files(self):
        for filename in ["tagmanifest-%s.txt" % a for a in checksum_algos]:
            f = os.path.join(self.path, filename)
            if isfile(f):
                yield f

    def compare_manifests_with_fs(self):
        files_on_fs = set(self.payload_files())
        files_in_manifest = set(self.payload_entries().keys())

        if self.version == "0.97":
            files_in_manifest = files_in_manifest | set(self.missing_optional_tagfiles())

        return (list(files_in_manifest - files_on_fs),
                list(files_on_fs - files_in_manifest))

    def compare_fetch_with_fs(self):
        """Compares the fetch entries with the files actually
           in the payload, and returns a list of all the files
           that still need to be fetched.
        """

        files_on_fs = set(self.payload_files())
        files_in_fetch = set(self.files_to_be_fetched())

        return list(files_in_fetch - files_on_fs)

    def payload_files(self):
        payload_dir = os.path.join(self.path, "data")

        for dirpath, dirnames, filenames in os.walk(payload_dir):
            for f in filenames:
                # Jump through some hoops here to make the payload files come out
                # looking like data/dir/file, rather than having the entire path.
                rel_path = os.path.join(dirpath, os.path.normpath(f.replace('\\', '/')))
                rel_path = rel_path.replace(self.path + os.path.sep, "", 1)
                yield rel_path

    def payload_entries(self):
        # Don't use dict comprehension (compatibility with Python < 2.7)
        return dict((key, value) for (key, value) in self.entries.items()
                    if key.startswith("data" + os.sep))

    def save(self, processes=1, manifests=False):
        """
        save will persist any changes that have been made to the bag
        metadata (self.info).

        If you have modified the payload of the bag (added, modified,
        removed files in the data directory) and want to regenerate manifests
        set the manifests parameter to True. The default is False since you
        wouldn't want a save to accidentally create a new manifest for
        a corrupted bag.

        If you want to control the number of processes that are used when
        recalculating checksums use the processes parameter.
        """
        # Error checking
        if not self.path:
            raise BagError("Bag does not have a path.")

        # Change working directory to bag directory so helper functions work
        old_dir = os.path.abspath(os.path.curdir)
        os.chdir(self.path)

        # Generate new manifest files
        if manifests:
            unbaggable = _can_bag(self.path)
            if unbaggable:
                logger.error("no write permissions for the following directories and files: \n%s", unbaggable)
                raise BagError("Not all files/folders can be moved.")
            unreadable_dirs, unreadable_files = _can_read(self.path)
            if unreadable_dirs or unreadable_files:
                if unreadable_dirs:
                    logger.error("The following directories do not have read permissions: \n%s", unreadable_dirs)
                if unreadable_files:
                    logger.error("The following files do not have read permissions: \n%s", unreadable_files)
                raise BagError("Read permissions are required to calculate file fixities.")

            oxum = None
            self.algs = list(set(self.algs))  # Dedupe
            for alg in self.algs:
                logger.info('updating manifest-%s.txt', alg)
                oxum = _make_manifest('manifest-%s.txt' % alg, 'data', processes, alg)

            # Update Payload-Oxum
            logger.info('updating %s', self.tag_file_name)
            if oxum:
                self.info['Payload-Oxum'] = oxum

        _make_tag_file(self.tag_file_name, self.info)

        # Update tag-manifest for changes to manifest & bag-info files
        for alg in self.algs:
            _make_tagmanifest_file(alg, self.path)

        # Reload the manifests
        self._load_manifests()

        os.chdir(old_dir)

    def tagfile_entries(self):
        return dict((key, value) for (key, value) in self.entries.items()
                    if not key.startswith("data" + os.sep))

    def missing_optional_tagfiles(self):
        """
        From v0.97 we need to validate any tagfiles listed
        in the optional tagmanifest(s). As there is no mandatory
        directory structure for additional tagfiles we can
        only check for entries with missing files (not missing
        entries for existing files).
        """
        for tagfilepath in list(self.tagfile_entries().keys()):
            if not os.path.isfile(os.path.join(self.path, tagfilepath)):
                yield tagfilepath

    def fetch_entries(self):
        fetch_file_path = os.path.join(self.path, "fetch.txt")

        if isfile(fetch_file_path):
            with open(fetch_file_path, 'rb') as fetch_file:
                for line in fetch_file:
                    parts = line.strip().split(None, 2)
                    yield (parts[0], parts[1], parts[2])

    def files_to_be_fetched(self):
        for f, size, path in self.fetch_entries():
            yield f

    def has_oxum(self):
        return 'Payload-Oxum' in self.info

    def validate(self, processes=1, fast=False):
        """Checks the structure and contents are valid. If you supply
        the parameter fast=True the Payload-Oxum (if present) will
        be used to check that the payload files are present and
        accounted for, instead of re-calculating fixities and
        comparing them against the manifest. By default validate()
        will re-calculate fixities (fast=False).
        """
        self._validate_structure()
        self._validate_bagittxt()
        self._validate_contents(processes=processes, fast=fast)
        return True

    def is_valid(self, fast=False):
        """Returns validation success or failure as boolean.
        Optional fast parameter passed directly to validate().
        """
        try:
            self.validate(fast=fast)
        except BagError as e:
            return False
        return True

    def _load_manifests(self):
        manifests = list(self.manifest_files())

        if self.version == "0.97":
            # v0.97 requires that optional tagfiles are verified.
            manifests += list(self.tagmanifest_files())

        for manifest_file in manifests:
            if not manifest_file.find("tagmanifest-") is -1:
                search = "tagmanifest-"
            else:
                search = "manifest-"
            alg = os.path.basename(manifest_file).replace(search, "").replace(".txt", "")
            self.algs.append(alg)

            with open(manifest_file, 'r') as manifest_file:
                for line in manifest_file:
                    line = line.strip()

                    # Ignore blank lines and comments.
                    if line == "" or line.startswith("#"): continue

                    entry = line.split(None, 1)

                    # Format is FILENAME *CHECKSUM
                    if len(entry) != 2:
                        logger.error("%s: Invalid %s manifest entry: %s", self, alg, line)
                        continue

                    entry_hash = entry[0]
                    entry_path = os.path.normpath(entry[1].lstrip("*"))
                    entry_path = _decode_filename(entry_path)

                    if entry_path in self.entries:
                        self.entries[entry_path][alg] = entry_hash
                    else:
                        self.entries[entry_path] = {}
                        self.entries[entry_path][alg] = entry_hash

    def _validate_structure(self):
        """Checks the structure of the bag, determining if it conforms to the
           BagIt spec. Returns true on success, otherwise it will raise
           a BagValidationError exception.
        """
        self._validate_structure_payload_directory()
        self._validate_structure_tag_files()

    def _validate_structure_payload_directory(self):
        data_dir_path = os.path.join(self.path, "data")

        if not isdir(data_dir_path):
            raise BagValidationError("Missing data directory")

    def _validate_structure_tag_files(self):
        # Note: we deviate somewhat from v0.96 of the spec in that it allows
        # other files and directories to be present in the base directory
        if len(list(self.manifest_files())) == 0:
            raise BagValidationError("Missing manifest file")
        if "bagit.txt" not in os.listdir(self.path):
            raise BagValidationError("Missing bagit.txt")

    def _validate_contents(self, processes=1, fast=False):
        if fast and not self.has_oxum():
            raise BagValidationError("cannot validate Bag with fast=True if Bag lacks a Payload-Oxum")
        self._validate_oxum()    # Fast
        if not fast:
            self._validate_entries(processes) # *SLOW*

    def _validate_oxum(self):
        oxum = self.info.get('Payload-Oxum')
        if oxum == None: return

        # If multiple Payload-Oxum tags (bad idea)
        # use the first listed in bag-info.txt
        if type(oxum) is list:
            oxum = oxum[0]

        byte_count, file_count = oxum.split('.', 1)

        if not byte_count.isdigit() or not file_count.isdigit():
            raise BagError("Invalid oxum: %s" % oxum)

        byte_count = int(byte_count)
        file_count = int(file_count)
        total_bytes = 0
        total_files = 0

        for payload_file in self.payload_files():
            payload_file = os.path.join(self.path, payload_file)
            total_bytes += os.stat(payload_file).st_size
            total_files += 1

        if file_count != total_files or byte_count != total_bytes:
            raise BagValidationError("Oxum error.  Found %s files and %s bytes on disk; expected %s files and %s bytes." % (total_files, total_bytes, file_count, byte_count))

    def _validate_entries(self, processes):
        """
        Verify that the actual file contents match the recorded hashes stored in the manifest files
        """
        errors = list()

        # First we'll make sure there's no mismatch between the filesystem
        # and the list of files in the manifest(s)
        only_in_manifests, only_on_fs = self.compare_manifests_with_fs()
        for path in only_in_manifests:
            e = FileMissing(path)
            logger.warning(str(e))
            errors.append(e)
        for path in only_on_fs:
            e = UnexpectedFile(path)
            logger.warning(str(e))
            errors.append(e)

        # To avoid the overhead of reading the file more than once or loading
        # potentially massive files into memory we'll create a dictionary of
        # hash objects so we can open a file, read a block and pass it to
        # multiple hash objects

        available_hashers = set()
        for alg in self.algs:
            try:
                hashlib.new(alg)
                available_hashers.add(alg)
            except ValueError:
                logger.warning("Unable to validate file contents using unknown %s hash algorithm", alg)

        if not available_hashers:
            raise RuntimeError("%s: Unable to validate bag contents: none of the hash algorithms in %s are supported!" % (self, self.algs))

        def _init_worker():
            signal.signal(signal.SIGINT, signal.SIG_IGN)

        args = ((self.path, rel_path, hashes, available_hashers) for rel_path, hashes in list(self.entries.items()))

        try:
            if processes == 1:
                hash_results = list(map(_calc_hashes, args))
            else:
                try:
                    pool = multiprocessing.Pool(processes if processes else None, _init_worker)
                    hash_results = pool.map(_calc_hashes, args)
                finally:
                    try:
                        pool.terminate()
                    except:
                        # we really don't care about any exception in terminate()
                        pass
        # Any unhandled exceptions are probably fatal
        except:
            logger.exception("unable to calculate file hashes for %s", self)
            raise

        for rel_path, f_hashes, hashes in hash_results:
            for alg, computed_hash in list(f_hashes.items()):
                stored_hash = hashes[alg]
                if stored_hash.lower() != computed_hash:
                    e = ChecksumMismatch(rel_path, alg, stored_hash.lower(), computed_hash)
                    logger.warning(str(e))
                    errors.append(e)

        if errors:
            raise BagValidationError("invalid bag", errors)

    def _validate_bagittxt(self):
        """
        Verify that bagit.txt conforms to specification
        """
        bagit_file_path = os.path.join(self.path, "bagit.txt")
        with open(bagit_file_path, 'r') as bagit_file:
            first_line = bagit_file.readline()
            if first_line.startswith(BOM):
                raise BagValidationError("bagit.txt must not contain a byte-order mark")


class BagError(Exception):
    pass

class BagValidationError(BagError):
    def __init__(self, message, details=[]):
        self.message = message
        self.details = details
    def __str__(self):
        if len(self.details) > 0:
            details = " ; ".join([str(e) for e in self.details])
            return "%s: %s" % (self.message, details)
        return self.message

class ManifestErrorDetail(BagError):
    def __init__(self, path):
        self.path = path

class ChecksumMismatch(ManifestErrorDetail):
    def __init__(self, path, algorithm=None, expected=None, found=None):
        self.path = path
        self.algorithm = algorithm
        self.expected = expected
        self.found = found
    def __str__(self):
        return "%s checksum validation failed (alg=%s expected=%s found=%s)" % (self.path, self.algorithm, self.expected, self.found)

class FileMissing(ManifestErrorDetail):
    def __str__(self):
        return "%s exists in manifest but not found on filesystem" % self.path

class UnexpectedFile(ManifestErrorDetail):
    def __str__(self):
        return "%s exists on filesystem but is not in manifest" % self.path


def _calc_hashes(args):
    # auto unpacking of sequences illegal in Python3
    (base_path, rel_path, hashes, available_hashes) = args
    full_path = os.path.join(base_path, rel_path)

    # Create a clone of the default empty hash objects:
    f_hashers = dict(
        (alg, hashlib.new(alg)) for alg in hashes if alg in available_hashes
    )

    try:
        f_hashes = _calculate_file_hashes(full_path, f_hashers)
    except BagValidationError as e:
        f_hashes = dict(
            (alg, str(e)) for alg in list(f_hashers.keys())
        )

    return rel_path, f_hashes, hashes


def _calculate_file_hashes(full_path, f_hashers):
    """
    Returns a dictionary of (algorithm, hexdigest) values for the provided
    filename
    """
    if not os.path.exists(full_path):
        raise BagValidationError("%s does not exist" % full_path)

    try:
        with open(full_path, 'rb') as f:
            while True:
                block = f.read(1048576)
                if not block:
                    break
                for i in list(f_hashers.values()):
                    i.update(block)
    except IOError as e:
        raise BagValidationError("could not read %s: %s" % (full_path, str(e)))
    except OSError as e:
        raise BagValidationError("could not read %s: %s" % (full_path, str(e)))

    return dict(
        (alg, h.hexdigest()) for alg, h in list(f_hashers.items())
    )


def _load_tag_file(tag_file_name):
    with open(tag_file_name, 'r') as tag_file:
        # Store duplicate tags as list of vals
        # in order of parsing under the same key.
        tags = {}
        for name, value in _parse_tags(tag_file):
            if not name in tags:
                tags[name] = value
                continue

            if not type(tags[name]) is list:
                tags[name] = [tags[name], value]
            else:
                tags[name].append(value)
        return tags

def _parse_tags(file):
    """Parses a tag file, according to RFC 2822.  This
       includes line folding, permitting extra-long
       field values.

       See http://www.faqs.org/rfcs/rfc2822.html for
       more information.
    """

    tag_name = None
    tag_value = None

    # Line folding is handled by yielding values only after we encounter
    # the start of a new tag, or if we pass the EOF.
    for num, line in enumerate(file):
        # If byte-order mark ignore it for now.
        if num == 0:
            if line.startswith(BOM):
                line = line.lstrip(BOM)
        # Skip over any empty or blank lines.
        if len(line) == 0 or line.isspace():
            continue
        elif line[0].isspace() and tag_value != None : # folded line
            tag_value += line
        else:
            # Starting a new tag; yield the last one.
            if tag_name:
                yield (tag_name, tag_value.strip())

            if not ':' in line:
                raise BagValidationError("invalid line '%s' in %s" % (line.strip(), os.path.basename(file.name)))

            parts = line.strip().split(':', 1)
            tag_name = parts[0].strip()
            tag_value = parts[1]

    # Passed the EOF.  All done after this.
    if tag_name:
        yield (tag_name, tag_value.strip())


def _make_tag_file(bag_info_path, bag_info):
    headers = list(bag_info.keys())
    headers.sort()
    with open(bag_info_path, 'w') as f:
        for h in headers:
            if type(bag_info[h]) == list:
                for val in bag_info[h]:
                    f.write("%s: %s\n" % (h, val))
            else:
                txt = bag_info[h]
                # strip CR, LF and CRLF so they don't mess up the tag file
                txt = re.sub('\n|\r|(\r\n)', '', txt)
                f.write("%s: %s\n" % (h, txt))


def _make_manifest(manifest_file, data_dir, processes, algorithm='md5'):
    logger.info('writing manifest with %s processes' % processes)

    if algorithm == 'md5':
        manifest_line = _manifest_line_md5
    elif algorithm == 'sha1':
        manifest_line = _manifest_line_sha1
    elif algorithm == 'sha256':
        manifest_line = _manifest_line_sha256
    elif algorithm == 'sha512':
        manifest_line = _manifest_line_sha512
    else:
        raise RuntimeError("unknown algorithm %s" % algorithm)

    if processes > 1:
        pool = multiprocessing.Pool(processes=processes)
        checksums = pool.map(manifest_line, _walk(data_dir))
        pool.close()
        pool.join()
    else:
        checksums = list(map(manifest_line, _walk(data_dir)))

    with open(manifest_file, 'w') as manifest:
        num_files = 0
        total_bytes = 0

        for digest, filename, bytes in checksums:
            num_files += 1
            total_bytes += bytes
            manifest.write("%s  %s\n" % (digest, _encode_filename(filename)))
        manifest.close()
        return "%s.%s" % (total_bytes, num_files)


def _make_tagmanifest_file(alg, bag_dir):
    tagmanifest_file = join(bag_dir, "tagmanifest-%s.txt" % alg)
    logger.info("writing %s", tagmanifest_file)
    files = [f for f in listdir(bag_dir) if isfile(join(bag_dir, f))]
    checksums = []
    for f in files:
        if re.match('^tagmanifest-.+\.txt$', f):
            continue
        with open(join(bag_dir, f), 'rb') as fh:
            m = _hasher(alg)
            while True:
                bytes = fh.read(16384)
                if not bytes:
                    break
                m.update(bytes)
            checksums.append((m.hexdigest(), f))

    with open(join(bag_dir, tagmanifest_file), 'w') as tagmanifest:
        for digest, filename in checksums:
            tagmanifest.write('%s %s\n' % (digest, filename))


def _walk(data_dir):
    for dirpath, dirnames, filenames in os.walk(data_dir):
        # if we don't sort here the order of entries is non-deterministic
        # which makes it hard to test the fixity of tagmanifest-md5.txt
        filenames.sort()
        dirnames.sort()
        for fn in filenames:
            path = os.path.join(dirpath, fn)
            # BagIt spec requires manifest to always use '/' as path separator
            if os.path.sep != '/':
                parts = path.split(os.path.sep)
                path = '/'.join(parts)
            yield path

def _can_bag(test_dir):
    """returns (unwriteable files/folders)
    """
    unwriteable = []
    for inode in os.listdir(test_dir):
        if not os.access(os.path.join(test_dir, inode), os.W_OK):
            unwriteable.append(os.path.join(os.path.abspath(test_dir), inode))
    return tuple(unwriteable)

def _can_read(test_dir):
    """
    returns ((unreadable_dirs), (unreadable_files))
    """
    unreadable_dirs = []
    unreadable_files = []
    for dirpath, dirnames, filenames in os.walk(test_dir):
        for dn in dirnames:
            if not os.access(os.path.join(dirpath, dn), os.R_OK):
                unreadable_dirs.append(os.path.join(dirpath, dn))
        for fn in filenames:
            if not os.access(os.path.join(dirpath, fn), os.R_OK):
                unreadable_files.append(os.path.join(dirpath, fn))
    return (tuple(unreadable_dirs), tuple(unreadable_files))

def _manifest_line_md5(filename):
    return _manifest_line(filename, 'md5')

def _manifest_line_sha1(filename):
    return _manifest_line(filename, 'sha1')

def _manifest_line_sha256(filename):
    return _manifest_line(filename, 'sha256')

def _manifest_line_sha512(filename):
    return _manifest_line(filename, 'sha512')

def _hasher(algorithm='md5'):
    if algorithm == 'md5':
        m = hashlib.md5()
    elif algorithm == 'sha1':
        m = hashlib.sha1()
    elif algorithm == 'sha256':
        m = hashlib.sha256()
    elif algorithm == 'sha512':
        m = hashlib.sha512()
    return m

def _manifest_line(filename, algorithm='md5'):
    with open(filename, 'rb') as fh:
        m = _hasher(algorithm)

        total_bytes = 0
        while True:
            bytes = fh.read(16384)
            total_bytes += len(bytes)
            if not bytes:
                break
            m.update(bytes)

    return (m.hexdigest(), _decode_filename(filename), total_bytes)

def _encode_filename(s):
    s = s.replace("\r", "%0D")
    s = s.replace("\n", "%0A")
    return s

def _decode_filename(s):
    s = re.sub("%0D", "\r", s, re.IGNORECASE)
    s = re.sub("%0A", "\n", s, re.IGNORECASE)
    return s


# following code is used for command line program

class BagOptionParser(optparse.OptionParser):
    def __init__(self, *args, **opts):
        self.bag_info = {}
        optparse.OptionParser.__init__(self, *args, **opts)

def _bag_info_store(option, opt, value, parser):
    opt = opt.lstrip('--')
    opt_caps = '-'.join([o.capitalize() for o in opt.split('-')])
    parser.bag_info[opt_caps] = value

def _make_opt_parser():
    parser = BagOptionParser(usage='usage: %prog [options] dir1 dir2 ...')
    parser.add_option('--processes', action='store', type="int",
                      dest='processes', default=1,
                      help='parallelize checksums generation and verification')
    parser.add_option('--log', action='store', dest='log')
    parser.add_option('--quiet', action='store_true', dest='quiet')
    parser.add_option('--validate', action='store_true', dest='validate')
    parser.add_option('--fast', action='store_true', dest='fast')

    # optionally specify which checksum algorithm(s) to use when creating a bag
    # NOTE: could generate from checksum_algos ?
    parser.add_option('--md5', action='append_const', dest='checksum', const='md5',
                      help='Generate MD5 manifest when creating a bag (default)')
    parser.add_option('--sha1', action='append_const', dest='checksum', const='sha1',
                      help='Generate SHA1 manifest when creating a bag')
    parser.add_option('--sha256', action='append_const', dest='checksum', const='sha256',
                      help='Generate SHA-256 manifest when creating a bag')
    parser.add_option('--sha512', action='append_const', dest='checksum', const='sha512',
                      help='Generate SHA-512 manifest when creating a bag')

    for header in _bag_info_headers:
        parser.add_option('--%s' % header.lower(), type="string",
                          action='callback', callback=_bag_info_store)
    return parser

def _configure_logging(opts):
    log_format="%(asctime)s - %(levelname)s - %(message)s"
    if opts.quiet:
        level = logging.ERROR
    else:
        level = logging.INFO
    if opts.log:
        logging.basicConfig(filename=opts.log, level=level, format=log_format)
    else:
        logging.basicConfig(level=level, format=log_format)

if __name__ == '__main__':
    opt_parser = _make_opt_parser()
    opts, args = opt_parser.parse_args()

    if opts.processes < 0:
        opt_parser.error("number of processes needs to be 0 or more")

    _configure_logging(opts)

    rc = 0
    for bag_dir in args:

        # validate the bag
        if opts.validate:
            try:
                bag = Bag(bag_dir)
                # validate throws a BagError or BagValidationError
                valid = bag.validate(processes=opts.processes, fast=opts.fast)
                if opts.fast:
                    logger.info("%s valid according to Payload-Oxum", bag_dir)
                else:
                    logger.info("%s is valid", bag_dir)
            except BagError as e:
                logger.info("%s is invalid: %s", bag_dir, e)
                rc = 1

        # make the bag
        else:
            try:
                make_bag(bag_dir, bag_info=opt_parser.bag_info,
                         processes=opts.processes,
                         checksum=opts.checksum)
            except Exception:
                logger.info("%s failed to create: %s", bag_dir, e)
                rc = 1

        sys.exit(rc)

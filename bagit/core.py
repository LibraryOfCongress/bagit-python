# Copyright (c) 2008
# This code was created by the Library of Congress and its National Digital
# Information Infrastructure and Preservation Program (NDIIPP) partners.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
# * Neither the name of the Library of Congress nor the names of its
# contributors may be used to endorse or promote products derived from this
# software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from glob import glob
from itertools import chain
import logging
import os
import hashlib

def load_tag_file(tag_file_name):
    tag_file = open(tag_file_name, "r")

    try:
        return dict(parse_tags(tag_file))
    finally:
        tag_file.close()

def parse_tags(file):
    """Parses a tag file, according to RFC 2822.  This
       includes line folding, permitting extra-long
       field values.

       See http://www.faqs.org/rfcs/rfc2822.html for
       more information.
    """

    tag_name = None
    tag_value = None

    # Line folding is handled by yielding values
    # only after we encounter the start of a new
    # tag, or if we pass the EOF.
    for line in file:
        # Skip over any empty or blank lines.
        if len(line) == 0 or line.isspace():
            continue

        if line[0].isspace(): # folded line
            tag_value += line.strip()
        else:
            # Starting a new tag; yield the last one.
            if tag_name:
                yield (tag_name, tag_value)

            parts = line.strip().split(':', 1)
            tag_name = parts[0].strip()
            tag_value = parts[1].strip()

    # Passed the EOF.  All done after this.
    if tag_name:
        yield (tag_name, tag_value)


class BagError(Exception):
    pass

class BagValidationError(BagError):
    pass

class Bag(object):
    """A representation of a bag."""

    path = None
    tags = {}
    entries = {}
    algs = []

    tag_file_name = None

    #: This list is used during validation to detect extra files in the top-level bag directory. Note that it will be extended to include the manifest and
    valid_files = ["bagit.txt", "fetch.txt"]
    valid_directories = ['data']

    def __init__(self, path=None):
        super(Bag, self).__init__()
        self.path = path

    def __unicode__(self):
        return u'Bag(path="%s")' % self.path

    @classmethod
    def load(cls, path, lenient=False):
        """Opens a bag in the given bag_dir, and returns a new Bag object.
           The bagit.txt is required
        """

        b = cls(path=path)

        try:
            b.open()
            b.validate()
        except BagValidationError, e:
            logging.warning("%s: validation error: %s", b.path, e)
            if not lenient:
                raise e

        return b

    def open(self):
        # Open the bagit.txt file, and load any tags from it, including
        # the required version and encoding.
        bagit_file_path = os.path.join(self.path, "bagit.txt")

        if not os.path.isfile(bagit_file_path):
            raise BagError("No bagit.txt found: %s" % bagit_file_path)

        self.tags = tags = load_tag_file(bagit_file_path)

        try:
            self.version = tags["BagIt-Version"]
            self.encoding = tags["Tag-File-Character-Encoding"]
        except KeyError, e:
            raise BagError("Missing required tag in bagit.txt: %s" % e)

        if self.version == "0.95":
            self.tag_file_name = "package-info.txt"
        elif self.version == "0.96":
            self.tag_file_name = "bag-info.txt"
        else:
            raise BagError("Unsupported bag version: %s" % self.version)

        if not self.encoding.lower() == "utf-8":
            raise BagValidationError("Unsupported encoding: %s" % self.encoding)

        info_file_path = os.path.join(self.path, self.tag_file_name)
        if os.path.exists(info_file_path):
            self.info = load_tag_file(info_file_path)

        self.load_manifests()

    def load_manifests(self):
        for manifest_file in self.manifest_files():
            alg = os.path.basename(manifest_file).replace("manifest-", "").replace(".txt", "")
            self.algs.append(alg)

            manifest_file = open(manifest_file, "r")

            try:
                for line in manifest_file:
                    line = line.strip()

                    # Ignore blank lines and comments.
                    if line == "" or line.startswith("#"): continue

                    entry = line.split(None, 1)

                    # Format is FILENAME *CHECKSUM
                    if len(entry) != 2:
                        logging.error("%s: Invalid %s manifest entry: %s", self, alg, line)
                        continue

                    entry_hash = entry[0]
                    entry_path = os.path.normpath(entry[1].lstrip("*"))

                    if self.entries.has_key(entry_path):
                        if self.entries[entry_path].has_key(alg):
                            logging.warning("%s: Duplicate %s manifest entry: %s", self, alg, entry_path)

                        self.entries[entry_path][alg] = entry_hash
                    else:
                        self.entries[entry_path] = {}
                        self.entries[entry_path][alg] = entry_hash
            finally:
                manifest_file.close()

    def manifest_files(self):
        for file in glob(os.path.join(self.path, "manifest-*.txt")):
            yield file

    def tagmanifest_files(self):
        for file in glob(os.path.join(self.path, "tagmanifest-*.txt")):
            yield file

    def compare_manifests_with_fs(self):
        files_on_fs = set(self.payload_files())
        files_in_manifest = set(self.entries.keys())

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

    def fetch_entries(self):
        fetch_file_path = os.path.join(self.path, "fetch.txt")

        if os.path.isfile(fetch_file_path):
            fetch_file = open(fetch_file_path, "r")

            try:
                for line in fetch_file:
                    parts = line.strip().split(None, 2)
                    yield (parts[0], parts[1], parts[2])
            finally:
                fetch_file.close()

    def files_to_be_fetched(self):
        for url, size, path in self.fetch_entries():
            yield path

    def urls_to_be_fetched(self):
        for url, size, path in self.fetch_entries():
            yield url

    def has_oxum(self):
        return self.tags.has_key('Payload-Oxum')

    def validate(self):
        self.validate_structure()
        self.validate_contents()

    def validate_structure(self):
        """Checks the structure of the bag, determining if it conforms to the
           BagIt spec.
        """
        self.validate_structure_payload_directory()
        self.validate_structure_tag_files()

    def validate_structure_payload_directory(self):
        data_dir_path = os.path.join(self.path, "data")

        if not os.path.isdir(data_dir_path):
            raise BagValidationError("Missing data directory.")

    def validate_structure_tag_files(self):
        # Files allowed in all versions are:
        #  - tagmanifest-<alg>.txt
        #  - manifest-<alt>.txt
        #  - bagit.txt
        #  - fetch.txt
        valid_files = list(self.valid_files)

        # The manifest files and tagmanifest files will start with {self.path}/
        # So strip that off.
        for f in chain(self.manifest_files(), self.tagmanifest_files()):
            valid_files.append(f[len(self.path) + 1:])

        for name in os.listdir(self.path):
            fullname = os.path.join(self.path, name)

            if os.path.isdir(fullname):
                if not name in self.valid_directories:
                    raise BagValidationError("Extra directory found: %s" % name)
            elif os.path.isfile(fullname):
                if not name in valid_files:
                    is_valid = self.validate_structure_is_valid_tag_file_name(name)
                    if not is_valid:
                        raise BagValidationError("Extra tag file found: %s" % name)
            else:
                # Something that's  neither a dir or a file. WTF?
                raise BagValidationError("Unknown item in bag: %s" % name)

    def validate_structure_is_valid_tag_file_name(self, file_name):
        return file_name == self.tag_file_name

    def validate_contents(self):
        """
        Validate the contents of this bag, which can be a very time-consuming
        operation
        """
        self.validate_oxum()    # Fast
        self.validate_entries() # *SLOW*

    def validate_oxum(self):
        """From John Kunze's email:
           The oxum is a so-called "poor man's checksum".  It counts the octet
           length of all the files in the payload and the number of the files
           on disk, and then concatenates them with a period.  Quoting Mr.
           Kunze:

           They are in the new BagIt V0.96 format, and the metadata includes the
           Payload-Oxum element in bag-info.txt (new name for package-info.txt).

           I'm not sure if you were on the phone calls when we discussed the
           "octetstream sum" (oxum), which is a two-part number that gives the total
           number of octets and number of streams (files).  For example, you'll find
           for the 2005-09 crawls

               Payload-Oxum: 527162265577.6597

           which means that the payload (not including the tag files) should contain
           exactly 527162265577 bytes and 6597 files.  In case you want to, it allows
           another check (a poor person's checksum) for accurate receipt of a bag.
        """
        oxum = self.tags.get('Payload-Oxum')
        if oxum == None: return

        byte_count, file_count = oxum.split('.', 1)

        if not byte_count.isdigit() or not file_count.isdigit():
            raise BagError("Invalid oxum: %s" % oxum)

        byte_count = long(byte_count)
        file_count = long(file_count)
        total_bytes = 0
        total_files = 0

        for payload_file in self.payload_files():
            payload_file = os.path.join(self.path, payload_file)
            total_bytes += os.stat(payload_file).st_size
            total_files += 1

        if file_count != total_files or byte_count != total_bytes:
            raise BagError("Oxum error.  Found %s files and %s bytes on disk; expected %s files and %s bytes." % (total_files, total_bytes, file_count, byte_count))

    def validate_entries(self):
        """
        Verify that the actual file contents match the recorded hashes stored in the manifest files
        """
        errors = list()

        # To avoid the overhead of reading the file more than once or loading
        # potentially massive files into memory we'll create a dictionary of
        # hash objects so we can open a file, read a block and pass it to
        # multiple hash objects

        hashers = {}
        for alg in self.algs:
            try:
                hashers[alg] = hashlib.new(alg)
            except KeyError:
                logging.warning("Unable to validate file contents using unknown %s hash algorithm", alg)

        if not hashers:
            raise RuntimeError("%s: Unable to validate bag contents: none of the hash algorithms in %s are supported!" % (self, self.algs))

        for rel_path, hashes in self.entries.items():
            full_path = os.path.join(self.path, rel_path)

            # Create a clone of the default empty hash objects:
            f_hashers = dict(
                (alg, h.copy()) for alg, h in hashers.items() if alg in hashes
            )

            try:
                f_hashes = self._calculate_file_hashes(full_path, hashers)
            except:
                # Any unhandled exceptions are probably fatal (e.g. file server issues) and recovery is dubious:
                logging.exception("%s: unable to calculate file hashes for %s: %s", self, full_path)
                raise

            for alg, stored_hash in f_hashes.items():
                computed_hash = f_hashes[alg]
                if stored_hash != computed_hash:
                    logging.warning("%s: stored hash %s doesn't match calculated hash %s", full_path, stored_hash, computed_hash)
                    errors.append("%s (%s)" % (full_path, alg))

        if errors:
            raise BagValidationError("%s: %d files failed checksum validation: %s" % (self, len(errors), errors))

    def _calculate_file_hashes(self, full_path, f_hashers):
        """
        Returns a dictionary of (algorithm, hexdigest) values for the provided
        filename
        """
        if not os.path.exists(full_path):
            raise BagValidationError("%s does not exist" % full_path)

        f = open(full_path, "rb")

        f_size = os.stat(full_path).st_size

        while f.tell() < f_size:
            block = f.read(1048576)
            [ i.update(block) for i in f_hashers.values() ]
        f.close()

        return dict(
            (alg, h.hexdigest()) for alg, h in f_hashers.items()
        )

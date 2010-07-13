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
from os import path

import sys, os


def open_bag(bag_dir, lenient = False):
    """Opens a bag in the given bag_dir, and returns a new Bag object.
       The bagit.txt is required, regardless of the lenient parameter.
    """
    # Open the bagit.txt file, and load any tags from it, including
    # the required version and encoding.
    bagit_file_path = path.join(bag_dir, "bagit.txt")
    
    if not path.isfile(bagit_file_path):
        raise BagError("No bagit.txt found: %s" % bagit_file_path)
    
    tags = load_tag_file(bagit_file_path)
    
    try:
        version = tags["BagIt-Version"]
        encoding = tags["Tag-File-Character-Encoding"]
    except KeyError, e:
        raise BagError("Missing required tag in bagit.txt: %s" % e)
    
    if version == "0.95":
        new_bag = Point95Bag()
    elif version == "0.96":
        new_bag = Point96Bag()
    else:
        raise BagError("Unsupported bag version: %s" % version)
    
    if encoding.upper() != "UTF-8" and not lenient:
        raise BagError("Unsupported tag file encoding: %s" % encoding)
    
    new_bag.dir = bag_dir
    new_bag.tags = tags
    new_bag.version = version
    new_bag.encoding = encoding
    new_bag.lenient = lenient
    
    new_bag.validate_structure()
    new_bag.open()
    
    return new_bag

def load_tag_file(tag_file_name, tag_map = {}):
    tag_file = open(tag_file_name, "r")
    
    try:
        for tag_name, tag_value in parse_tags(tag_file):
            tag_map[tag_name] = tag_value
    finally:
        tag_file.close()
        
    return tag_map

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
        if len(line) == 0 or line.isspace(): continue

        if line[0].isspace(): # folded line
            tag_value += line.strip()
        else:
            # Starting a new tag; yield the last one.
            yield (tag_name, tag_value)

            parts = line.strip().split(':', 1)
            tag_name = parts[0].strip()
            tag_value = parts[1].strip()

    # Passed the EOF.  All done after this.
    if tag_name: yield (tag_name, tag_value)


class BagError(Exception):
    def __init__(self, message):
        self.message = message
    
    def __str__(self):
        return repr(self.message)

class Bag:
    """A representation of a bag."""
    def __init__(self):
        self.dir = dir
        self.tags = {}
        self.entries = {}
        self.algs = []
        self.lenient = False
        
    def open(self):
        raise RuntimeError("Not implemented: open()")
        
    def load_tags(self):
        raise RuntimeError("Not implemented: load_tags()")
        
    def validate_structure(self):
        """Checks the structure of the bag, determining if it conforms to the
           BagIt spec.
        """
        self.validate_structure_payload_directory()
        self.validate_structure_tag_files()
            
    def validate_structure_payload_directory(self):
        data_dir_path = os.path.join(self.dir, "data")
        
        if not os.path.isdir(data_dir_path):
            if not self.lenient: raise BagError("Missing data directory.")
            
    def validate_structure_tag_files(self):
        # Files allowed in all versions are:
        #  - tagmanifest-<alg>.txt
        #  - manifest-<alt>.txt
        #  - bagit.txt
        #  - fetch.txt
        allowed_files = ["bagit.txt", "fetch.txt"]

        # The manifest files and tagmanifest files will start with {self.dir}/
        # So strip that off.
        allowed_files += [fullpath[len(self.dir) + 1:] for fullpath in list(self.manifest_files()) + list(self.tagmanifest_files())]
        
        for name in os.listdir(self.dir):
            fullname = path.join(self.dir, name)

            if path.isdir(fullname):
                if name == "data": continue # Ignore the payload directory
                if not self.lenient:
                    raise BagError("Extra directory found: %s" % name)
            elif path.isfile(fullname):
                if not name in allowed_files:
                    is_valid = self.validate_structure_is_valid_tag_file_name(name)
                    if not is_valid and not self.lenient:
                        raise BagError("Extra tag file found: %s" % name)
            elif not self.lenient:
                # Something that's  neither a dir or a file. WTF?
                raise BagError("Unknown item in bag: %s" % name)
                
    def validate_structure_is_valid_tag_file_name(self):
        raise RuntimeError("Not implemented: validate_structure_tag_file_name()")
        
    def open(self):
        self.load_tags()    
    
        for manifest_file in self.manifest_files():
            alg = path.basename(manifest_file).replace("manifest-", "").replace(".txt", "")
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
                        print "*** Invalid %s manifest entry: %s" % (alg, line)
                        continue
                    
                    entry_hash = entry[0]
                    entry_path = path.normpath(entry[1].lstrip("*"))
                    
                    if self.entries.has_key(entry_path):
                        if self.entries[entry_path].has_key(alg):
                            print "*** Duplicate %s manifest entry: %s" % (alg, entry_path)

                        self.entries[entry_path][alg] = entry_hash
                    else:
                        self.entries[entry_path] = {}
                        self.entries[entry_path][alg] = entry_hash
            finally:
                manifest_file.close()
                
    def manifest_files(self):
        for file in glob(path.join(self.dir, "manifest-*.txt")):
            yield file
            
    def tagmanifest_files(self):
        for file in glob(path.join(self.dir, "tagmanifest-*.txt")):
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
        payload_dir = os.path.join(self.dir, "data")
        
        for dirpath, dirnames, filenames in os.walk(payload_dir):
            for f in filenames:
                # Jump through some hoops here to make the payload files come out
                # looking like data/dir/file, rather than having the entire path.
                rel_path = os.path.join(dirpath, os.path.normpath(f.replace('\\', '/')))
                rel_path = rel_path.replace(self.dir + os.path.sep, "", 1)
                yield rel_path
                
    def fetch_entries(self):
        fetch_file_path = os.path.join(self.dir, "fetch.txt")
        
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
            
    def has_oxum(self): return self.tags.has_key('Payload-Oxum')
            
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
            payload_file = path.join(self.dir, payload_file)
            total_bytes += os.stat(payload_file).st_size
            total_files += 1
            
        if file_count != total_files or byte_count != total_bytes:
            raise BagError("Oxum error.  Found %s files and %s bytes on disk; expected %s files and %s bytes." % (total_files, total_bytes, file_count, byte_count))
            
class EarlyVersionBag(Bag):
    def validate_structure_is_valid_tag_file_name(self, file_name):
        return file_name == self.TAG_FILE_NAME
        
    def load_tags(self):
        tag_file_path = path.join(self.dir, self.TAG_FILE_NAME)
        
        if path.isfile(tag_file_path):
            load_tag_file(tag_file_path, self.tags)
            
class Point95Bag(EarlyVersionBag):
    TAG_FILE_NAME = "package-info.txt"
    
class Point96Bag(EarlyVersionBag):
    TAG_FILE_NAME = "bag-info.txt"

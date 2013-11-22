#!/usr/bin/env python

import os
import sys
import re
import argparse
from fnmatch import fnmatch
from zipfile import ZipFile

opts = {}

"""
Summary:

    Builds an installation zip file for a DBA to run.

Examples:

    zipinstall                  ==> look for install-*.sql and generate install.zip containing install/install-*sql and any files needed
                                    (simple case -- files must exist from CWD down; does not look in parent directories; first script found wins)
    zipinstall 1.0.11.3         ==> run this at the install or pending-install level or above; it will look for an install script in 
                                    a directory starting with REL-1.0.11.3, and generate REL-1.0.11.3.zip

Synopsis:

    starting with the current working directory
    look for files of the form: install-*.sql

    if found:
        create a new zip file
        open install sql file and look for lines starting with @
        for each @ file found:
            add that file to the zip file
        close zip file
"""

def read_options():
    parser = argparse.ArgumentParser(description='Generates an install zip file for a DBA')
    parser.add_argument('-f', '--file_template', metavar='FILE_TEMPLATE', default='install-*.sql', help='describes the install file name pattern to look for (default: install-*.sql)')
    parser.add_argument('--dry_run', default=False, action='store_true', help='disables writing the zip file, just displays what it would contain')
    parser.add_argument('-d', '--debug_enabled', default=False, action='store_true', help='enable debug output')   
    parser.add_argument('-v', '--verbose', default=False, action='store_true', help='enable verbose mode')
    parser.add_argument('path_template', default=None, nargs='?', help='[optional] the path segment install file should be in (note: A.B => REL-A.B)')
    return parser.parse_args(sys.argv[1:])

def debug(text):
    if opts.debug_enabled:
        print("[DEBUG] %s" % text)

def is_verbose():
    return opts.verbose        

def show(str, always=False):
    if is_verbose() or always:
        print(str)

def has_ext(filespec):
    return os.path.splitext(filespec)[1]

def strip_ext(filename):
    """
    Example: install.zip ==> install
    """
    return os.path.splitext(filename)[0]

def is_dotted_number(st):
    """
    True value if st of the form "1.1" or "10.1.17" or "10.10.10.10" etc.
    """
    return st and re.match('^\d+(\.\d+)+$', st) or None
       
def expected_path():
    """
    the optional expected path containing install script, allowing 1.1 to be shortcut for REL-1.1
    """
    return is_dotted_number(opts.path_template) and ("REL-%s" % opts.path_template) or opts.path_template 

def zip_filename():
    """
    the file name of the to-be-output zip file
    """
    return "%s.zip" % (expected_path() or "install")

def scan_install_path(current_path, expected_path, expected_file_pattern):
    """
    starting at current_path, 
    look for an install script file matching the expected file pattern (e.g. install-*.sql)
    ensuring it exists somewhere underneath a directory matching the expected path

    return the name of the found script
           as well as all the files encountered under current_path (used when generating zip later)
    """

    script_file = None
    file_tree = []
    debug("install script file pattern: %s" % expected_file_pattern)
    for path,dirs,files in os.walk(current_path):
        for f in files:
            filespec = os.path.join(path, f)
            file_tree.append(filespec)
            if fnmatch(f, expected_file_pattern):
                debug("potential script is %s" % filespec)
                debug("expected dir pattern is %s" % expected_path)
                if path_matches_dir(filespec, expected_path) and not script_file:
                    script_file = filespec
    return (script_file, file_tree)

def path_matches_dir(filespec, dir_snippet):
    """
    True if the given filespec contains the given dir_snippet either at the start or end of a directory name
    
    examples: path_contains_dir("pending-install/REL-1.0-my-install/mytable.tab", "REL-1.0")    ==> True
              path_contains_dir("pending-install/REL-1.0-my-install/mytable.tab", "my-install") ==> True
              path_contains_dir("pending-install/REL-1.0-my-install/mytable.tab", "my")         ==> False
              path_contains_dir("pending-install/REL-1.0-my-install/mytable.tab", None)         ==> True
    """

    if not dir_snippet:
        return True
    while filespec:
        (filespec, part) = os.path.split(filespec)
        debug("expecting %s to start or end with %s" % (part, dir_snippet))
        if part.startswith(dir_snippet) or part.endswith(dir_snippet):
            debug("expected dir found: %s/%s" % (filespec, part))
            return True
    return False

def find_file_in_tree(some_file, file_tree):
    if some_file.startswith(".") or some_file.startswith("/") or some_file.startswith("\\"):
        raise Exception("relative paths not supported")
    for filespec in file_tree:
        #debug("find f:%s fn:%s os.path.basename(f):%s" % (f, fn, os.path.basename(f)))
        if os.path.basename(filespec) == some_file:
            return filespec

def locate_referred_file(text):
    """
    the file specification of a file mentioned in an install script
    """
    filespec = None
    if text.startswith("@"):
        possible_file = text[1:].split()[0]
        if not has_ext(possible_file):
            possible_file = "%s.sql" % possible_file
        debug("looking for %s" % possible_file)
        filespec = find_file_in_tree(possible_file, file_tree)
        if not filespec:
            raise Exception("Could not find file metioned in line: %s" % text)
    return filespec

def generate_zip_file(zip_name, install_file, file_tree):
    files_to_include = [install_file]
    if not install_file:
        print("Nothing to do")
    else:
        print("%s %s ..." % (not opts.dry_run and "Creating" or "Would be", zip_name))
        try:
            f = file(install_file, "r")
            contents = [row.strip() for row in f.readlines()]
            for row in contents:
                zip_content_file = locate_referred_file(row)
                if zip_content_file and not zip_content_file in files_to_include:
                    files_to_include.append(zip_content_file)
                    debug("FILE:%s" % zip_content_file)
        finally:
            f.close()

        # n.b. with ZipFile(zip_name, "w") as install_zip: (takes care of close)
        try:
            if not opts.dry_run:
                install_zip = ZipFile(zip_name, "w")
            for filename in files_to_include:
                filespec_in_archive = "%s/%s" % (strip_ext(zip_name), os.path.basename(filename))
                show("... ENTRY: %s" % filespec_in_archive, always=opts.dry_run)
                if not opts.dry_run:
                    install_zip.write(filename, filespec_in_archive)
        finally:
            if not opts.dry_run:
                install_zip.close()

# ________________________

if __name__ == "__main__":
# ________________________ 

    opts = read_options()

    (script, file_tree) = scan_install_path(".", expected_path(), opts.file_template)

    debug("all files encountered:\n   %s" % "\n  ".join(file_tree))
    debug("script=%s" % script)

    generate_zip_file(zip_filename(), script, file_tree)

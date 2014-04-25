#!/usr/bin/env python

import os
import re
import sys
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
from glob import glob
from fnmatch import fnmatch
from zipfile import ZipFile

VERSION = 1.1

opts = {}

"""
Summary:
    Builds an installation zip file for a DBA to run.

Examples:
    zipinstall              ==> will look for install script (of the pattern install-*.sql) from the CWD down
                                (first one found wins), and generate install.zip containing install/install-*sql 
                                and any files needed.

    zipinstall 1.0.11.3     ==> run this at the root of a project; it will look for an install script in 
                                a directory matching REL-1.0.11.3, and generate REL-1.0.11.3.zip
"""

def read_options():
    help = """
        Generates an install zip file for a DBA. Version %s
        
        Example Usage:

        Step 1: Create a subdirectory for the installation. The naming convention is project-version/stage
        where project is like ssy-3.35 and stage is a sequential number starting with 1

        .../Db-Pos-Storeord/install$ mkdir ssy-3.35
        .../Db-Pos-Storeord/install/ssy-3.35$ mkdir 1


        Step 2: Create install script template
        .../Db-Pos-Storeord/install$ zipinstall -I -s STOREORD -n 3.35

        (creates: .../Db-Pos-Storeord/install/ssy-3.35/1/install.sql)

        Step 3: Edit the custom section within install.sql
        Prefix database object files to include with an @ sign only without subdirectory names.

        Example:
        -- ***** BEGIN CUSTOM SECTION *****
        @my_synonym.syn
        @my_view.vw
        @my_table.tab
        -- ***** END CUSTOM SECTION *****


        Step 4: Create the installation artifact:

        .../Db-Pos-Storeord/install$ zipinstall

        This creates: .../Db-Pos-Storeord/install/artifacts/ssy-3.35.zip
        containing:
                install/artifacts/REL-3.35/install-3.35.sql
                install/artifacts/REL-3.35/my_synonym.syn
                install/artifacts/REL-3.35/my_view.vw
                install/artifacts/REL-3.35/my_table.tab

    """ % VERSION

    parser = ArgumentParser(formatter_class=RawDescriptionHelpFormatter, description=help)
    parser.add_argument('-t', '--file_template', metavar='FILE_TEMPLATE', default='install*.sql', 
                        help='describes the install file name pattern to look for (default: install-*.sql)')
    parser.add_argument('--dry_run', default=False, action='store_true', 
                        help='disables writing the zip file, just displays what it would contain')
    parser.add_argument('-L', '--include_list', default=False, action='store_true',
                        help='generate list of files inside install script (with -I)')
    parser.add_argument('-I', '--build_install_script', default=False, action='store_true', 
                        help='used to generate an install template; REQUIRED: -s OPTIONAL: -n')
    parser.add_argument('-n', '--install_version', default=None, 
                        help='used to explicitly specify the install version for -I (e.g. 1.0.5)')
    parser.add_argument('-s', '--install_schema', default=None, 
                        help='used to specify the install schema for -I (e.g. CUSTOMER')
    parser.add_argument('-p', '--install_pathname', metavar='INSTALL_PATH', default='install', 
                        help='the path name containing or to contain the installation source (default: install)')
    parser.add_argument('-F', dest='force_overwrite', default=False, action='store_true',
                        help='used to force overwriting of existing files')
    parser.add_argument('-d', '--debug_enabled', default=False, action='store_true', 
                        help='enable debug output')   
    parser.add_argument('-v', '--verbose', default=False, action='store_true', 
                        help='enable verbose mode')
    parser.add_argument('path_template', default=None, nargs='?', 
                        help='[optional] the path segment install file should be in (note: A.B => REL-A.B)')
    options = parser.parse_args(sys.argv[1:])

    if options.build_install_script and not options.install_schema:
        parser.error("Schema option (-s) required if building install script (-I); -h for more info")

    return options

def debug(text):
    if opts.debug_enabled:
        print("[DEBUG] %s" % text)

def is_verbose():
    return opts.verbose        

def maybe_show(str, always=False):
    if is_verbose() or always:
        print(str)

def show(str):
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

def install_file_content(version='VERSION', schema='SCHEMA', file_list=[]):
    return """
-- spool output to a logfile
column spoolfile new_value v_spoolfile
select 'install-' || sys_context('USERENV','DB_NAME') || '-%s-' || to_char(sysdate,'yyyymmdd') || '.out' as spoolfile 
  from dual;
spool &v_spoolfile.

select 'Starting Install: ' || to_char(sysdate, 'yyyy-mm-dd DY hh24:mi:ss') as start_script from dual;

set serveroutput on;
set echo on;
set define off;
set timing on;

-- set the default schema for all scripts
ALTER SESSION SET CURRENT_SCHEMA=%s;

-- ***** BEGIN CUSTOM SECTION *****
%s
%s
-- ***** END CUSTOM SECTION *****

select 'Ending Install: '||to_char(sysdate, 'yyyy-mm-dd DY hh24:mi:ss') 
as end_script from dual;

spool off;
    """ % (version, 
           schema, 
           "-- file list (might need reordering):" if file_list else "",
           "\n".join(file_list))

def is_relevant_file(filespec):
    return not filespec.endswith(".DS_Store") and not filespec.startswith("./.git")

def scan_install_path(current_path, expected_path_pattern, expected_file_pattern):
    """
    starting at current_path, 
    look for an install script file matching the expected file pattern (e.g. install-*.sql)
    ensuring it exists somewhere underneath a directory matching the expected path

    return the name of the found script
           and a list of all the files encountered under current_path (used when generating zip later)
    """

    script_file = None
    script_subdir = None
    file_tree = []
    debug("looking for install script of the pattern: %s" % expected_file_pattern)
    for path,dirs,files in os.walk(current_path):
        for filespec in filter(lambda x: is_relevant_file(x), [os.path.join(path, f) for f in files]):
            debug("  filespec %s" % filespec)
            file_tree.append(filespec)
            if not script_file and fnmatch(os.path.basename(filespec), expected_file_pattern):
                debug("potential script is %s" % filespec)
                debug("expected dir pattern is %s" % expected_path_pattern)
                matching_subdir = find_matching_subdir(filespec, expected_path_pattern)
                if matching_subdir:
                    script_file = filespec
                    script_subdir = matching_subdir
                    debug("matching subdir = %s" % matching_subdir)
    return (script_file, script_subdir, file_tree)

# this needs to change ;::
def find_matching_subdir(filespec, dir_snippet):
    """
    given a full filespec and a directory snippet (e.g. 1.0.1), returns the actual subdirectory matching the
    snippet if the filespec is found underneath that subdirectory.
    (to match, a subdir has to match the snippet or match snippet followed by a dash)

    if no dir_snippet given, return the parent directory of the filespec

    examples: find_matching_subdir("pending-install/REL-1.0-my-install/mytable.tab", "REL-1.0")    
              ==> REL-1.0-my-install

              find_matching_subdir("pending-install/REL-1.0-my-install/mytable.tab", "asdf")         
              ==> None

              find_matching_subdir("pending-install/REL-1.0-my-install/mytable.tab", None)         
              ==> REL-1.0-my-install
    """

    debug("find_matching_subdir(%s, %s)" % (filespec, dir_snippet))
    while filespec:
        (filespec, part) = os.path.split(filespec)
        debug("trying to find subdir matching %s from %s,%s" % (dir_snippet, filespec, part))
        if not dir_snippet or part == dir_snippet or part.startswith("%s-" % dir_snippet):
            debug("expected dir found: %s/%s" % (filespec, part))
            return part
    return None

def find_file_in_tree(some_file, file_tree):
    if some_file.startswith(".") or some_file.startswith("/") or some_file.startswith("\\"):
        raise Exception("relative paths in referenced filenames not supported")
    for filespec in file_tree:
        #debug("find f:%s fn:%s os.path.basename(f):%s" % (f, fn, os.path.basename(f)))
        if os.path.basename(filespec) == some_file:
            return filespec

def locate_referred_file(text, file_tree):
    """
    the file specification of a file mentioned in the install script
    e.g. @customer.tab
    """
    filespec = None
    if text.startswith("@"):
        possible_file = text[1:].split()[0]
        if not has_ext(possible_file):
            possible_file = "%s.sql" % possible_file
        debug("looking for %s" % possible_file)
        filespec = find_file_in_tree(possible_file, file_tree)
        if not filespec:
            raise Exception("Could not find file mentioned in the line: %s" % text)
    return filespec

def generate_zip_file(zip_name, install_file, file_tree):
    message = None
    debug("Install file is: %s" % install_file)
    zipentry_path = os.path.dirname(install_file)
    files_to_include = [install_file]
    if not install_file:
        return (None, "Unknown install script")
    else:
        maybe_show("Zip file %s ..." % zip_name, always=opts.dry_run)
        try:
            f = file(install_file, "r")
            contents = [row.strip() for row in f.readlines()]
            for row in contents:
                zip_content_file = locate_referred_file(row, file_tree)
                if zip_content_file and not zip_content_file in files_to_include:
                    files_to_include.append(zip_content_file)
                    debug("FILE:%s" % zip_content_file)
        finally:
            f.close()

        # n.b. with ZipFile(zip_name, "w") as install_zip: (takes care of close)
        try:
            install_zip = None
            if opts.dry_run:
                message = "Nothing written (dry run)"
            else:
                if os.path.isfile(zip_name) and not opts.force_overwrite:
                    message = "File %s exists; add -F option to overwrite" % zip_name
                else:
                    install_zip = ZipFile(zip_name, "w")
                    message = "File created:"
            for filename in files_to_include:
                debug("ZIP file to include: %s" % filename)
                filespec_in_archive = "%s/%s" % (zipentry_path, os.path.basename(filename))
                maybe_show("... ENTRY: %s" % filespec_in_archive, always=opts.dry_run)
                if install_zip:
                    install_zip.write(filename, filespec_in_archive)
        finally:
            if install_zip:
                install_zip.close()

        return (install_zip and install_zip.filename or None, message)

def cwd_name():
    return os.path.basename(os.getcwd())        

def change_to_zip_starting_dir():
    for parent_dir_count in range(3):
        child_dir = os.path.join(os.getcwd(), opts.install_pathname)
        if os.path.isdir(child_dir):
            return
        os.chdir("..")
    show("Please run from inside or above the %s directory" % opts.install_pathname)
    sys.exit()

def write_file(filename, content):
    if os.path.isfile(filename):
        show("File %s already exists" % os.path.abspath(filename))
        if not opts.force_overwrite:
            return
    try:
        f = file(filename, 'w')
        f.writelines(content)
        show("File '%s' written" % os.path.abspath(filename))
    finally:
        f.close()

def filenames_to_include(excepting=None, prefix='@'):
    to_include = []
    if opts.include_list:
        to_include = ["%s%s" % (prefix, x) for x in glob("*") if x != excepting]
    return to_include

def derive_install_version():
    return cwd_name().split("REL-")[-1]

def get_install_script_details():
    version = opts.install_version or derive_install_version() or "N.N.N"
    schema = (opts.install_schema or "MISSING_SCHEMA").upper()
    filename_template = opts.file_template.replace("*", "%s")
    filename = os.path.join(".", filename_template % version)
    return (filename, version, schema)

def build_install_script_template():
    ideal_dirname = "REL-%s" % opts.install_version
    if not cwd_name() == ideal_dirname:
        if cwd_name() == opts.install_pathname:
            if os.path.exists(ideal_dirname):
                os.chdir(ideal_dirname)
            else:
                os.makedirs(ideal_dirname)
                os.chdir(ideal_dirname)
    (filename, version, schema) = get_install_script_details()                
    file_content = install_file_content(version, schema, filenames_to_include(excepting=filename))
    write_file(filename, file_content)

def get_expected_path():
    """
    the optional expected path containing install script, allowing 1.1 to be shortcut for REL-1.1
    """
    if opts.path_template:
        if is_dotted_number(opts.path_template):
            return "REL-%s" % opts.path_template
        else:
            return opts.path_template
    else:
        return cwd_name()

def build_zip_file():
    """
    starting with the current working directory
    look for files of the form: install-*.sql

    if found:
        create a new zip file
        open install sql file and look for lines starting with @
        for each @ file found:
            add that file to the zip file
        close zip file
    """

    debug("CWD %s" % os.getcwd())
    expected_path = get_expected_path()
    change_to_zip_starting_dir()
    (script, actual_path, file_tree) = scan_install_path(".", expected_path, opts.file_template)
    debug("actual path %s" % actual_path)
    debug("all files encountered:\n   %s" % "\n  ".join(file_tree))
    debug("script=%s" % script)

    artifacts_dir = "%s/artifacts" % opts.install_pathname
    if not os.path.exists(artifacts_dir):
        os.makedirs(artifacts_dir)
    (zip_file, message) = generate_zip_file("%s/%s.zip" % (artifacts_dir, actual_path), script, file_tree)

    if message:
        show(message)
    if zip_file:
        show(os.path.abspath(zip_file))

# ________________________

if __name__ == "__main__":
# ________________________ 

    opts = read_options()
    if opts.build_install_script:
        build_install_script_template()
    else:
        build_zip_file()
        
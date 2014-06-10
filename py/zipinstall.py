#!/usr/bin/env python

import os
import re
import sys
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
from glob import glob
from fnmatch import fnmatch
from zipfile import ZipFile

VERSION = "1.3.1"
NAME = "zipinstall"

opts = {}


"""
Summary:
    Builds an installation zip file for a DBA to run.
"""

def read_options():
    help = """
        Generates an install zip file for a DBA. Version %s.

        For detailed usage, %s -u
    """ % (VERSION, NAME)

    script = NAME
    usage_help = """
        Usage

        Step 1: Initialize the install script. Example:
        .../Db-Pos-Storeord/install$ %(script)s -I -s STOREORD -n ssy-3.35

        or:
        .../Db-Pos-Storeord/install/ssy-3.35$ %(script)s -I -s STOREORD

        This example creates Db-Pos-Storeord/install/ssy-3.35/1/install.sql)

        Step 2: Edit the custom section within install.sql
        Prefix database object files to include with an @ sign (without subdirectory name). Example:

        -- ***** BEGIN CUSTOM SECTION *****
        @my_synonym.syn
        @my_view.vw
        @my_table.tab
        -- ***** END CUSTOM SECTION *****


        Step 3: Create the installation artifact. Example:
        .../Db-Pos-Storeord/install/ssy-3.35$ %(script)s

        This example creates: .../Db-Pos-Storeord/install/artifacts/install-ssy-3.35-1.zip
        containing:
                install/artifacts/ssy-3.35/1/install.sql
                install/artifacts/ssy-3.35/1/my_synonym.syn
                install/artifacts/ssy-3.35/1/my_view.vw
                install/artifacts/ssy-3.35/1/my_table.tab
        """ % locals()

    parser = ArgumentParser(formatter_class=RawDescriptionHelpFormatter, description=help)
    parser.add_argument('-u', '--usage', default=False, action='store_true',
                        help='show usage, and exit')
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
    parser.add_argument('--repo_prefix', metavar='REPO_PREFIX', default='Db-',
                        help='the prefix string for repository names (default: Db-')
    parser.add_argument('-F', dest='force_overwrite', default=False, action='store_true',
                        help='used to force overwriting of existing files')
    parser.add_argument('-d', '--debug_enabled', default=False, action='store_true',
                        help='enable debug output')
    parser.add_argument('-v', '--verbose', default=False, action='store_true',
                        help='enable verbose mode')
    parser.add_argument('path_template', default=None, nargs='?',
                        help='[optional] the path segment an install file should be in')
    options = parser.parse_args(sys.argv[1:])

    if options.usage:
        abort(usage_help)

    if options.build_install_script and not options.install_schema:
        parser.error("Schema option (-s) required if building install script (-I); %s -h for more info" % NAME)

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

def cwd_name():
    return os.path.basename(os.getcwd())

def cwd_parent():
    return os.path.basename(os.path.dirname(os.getcwd()))

def abort(msg=None):
    if msg:
        show(msg)
    sys.exit()

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

def fixpath(path):
    """
    renders path string in the correct format for the running system
    """
    return path.replace("/", os.sep)

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
    return not filespec.endswith(".DS_Store") \
        and not filespec.startswith(fixpath("./.git")) \
        and not filespec.startswith(fixpath("./install/completed/")) \
        and not filespec.startswith(fixpath("./install/artifacts"))

def scan_install_path(current_path, expected_path_pattern, expected_file_pattern):
    """
    starting at current_path,
    look for an install script file matching the expected file pattern (e.g. install-*.sql)
    ensuring it exists somewhere underneath a directory matching the expected path

    return the name of the found script
           and a list of all the files encountered under current_path (used when generating zip later)
    """

    script_files = []
    file_tree = []
    previously_matched_subdir = None
    debug("looking for install script of the pattern: %s" % expected_file_pattern)
    for path,dirs,files in os.walk(current_path):
        for filespec in filter(lambda x: is_relevant_file(x), [os.path.join(path, f) for f in files]):
            debug("  filespec %s" % filespec)
            file_tree.append(filespec)
            if fnmatch(os.path.basename(filespec), expected_file_pattern):
                debug("potential script is %s" % filespec)
                debug("expected dir pattern is %s" % expected_path_pattern)
                matching_subdir = find_matching_subdir(filespec, expected_path_pattern)
                if matching_subdir:
                    if previously_matched_subdir and matching_subdir != previously_matched_subdir:
                        show("Skipping duplicate '%s' as it matches '%s', but not '%s'" % \
                              (matching_subdir, expected_path_pattern, previously_matched_subdir))
                    else:
                        script_files.append(filespec)
                        if not previously_matched_subdir:
                            show("Building installation for '%s'" % matching_subdir)
                        previously_matched_subdir = matching_subdir
                        debug("adding matched subdir (%s)" % matching_subdir)

    return (script_files, file_tree)

def find_matching_subdir(filespec, dir_snippet):
    """
    given a full filespec and a directory snippet (e.g. 1.0.1), returns the actual subdirectory matching the
    snippet if the filespec is found within the subdirectory tree.
    (to match, the snippet must be the same as the subdirectory or be the suffix of a subdirectory)

    examples: find_matching_subdir("./install/ssy-1.0.0/1/install.sql", "1.0.0")
              ==returns==> ssy-1.0.0

              find_matching_subdir("./install/ssy-1.0.0/1/install.sql", "XYZZY")
              ==returns==> None
    """

    debug("find_matching_subdir(%s, %s)" % (filespec, dir_snippet))
    while filespec:
        (filespec, part) = os.path.split(filespec)
        debug("trying to find subdir matching %(dir_snippet)s from %(filespec)s,%(part)s" % locals())
        if not dir_snippet or part == dir_snippet or part.endswith("-%s" % dir_snippet):
            debug("expected dir found: %(filespec)s/%(part)s" % locals())
            return part
    return None

def find_file_in_tree(some_file, file_tree):
    if some_file.startswith(".") or some_file.startswith(fixpath("/")):
        abort("!! Error: relative paths in referenced filenames not supported: %s" % some_file)
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
            abort("!! Error: could not find file mentioned in the line: %s" % text)
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
                    message = "!! File exists: %s; use -F option to overwrite" % zip_name
                else:
                    install_zip = ZipFile(zip_name, "w")
                    message = "File created:"
            for filename in files_to_include:
                debug("ZIP file to include: %s" % filename)
                filespec_in_archive = fixpath("%s/%s" % (zipentry_path, os.path.basename(filename)))
                maybe_show("... ENTRY: %s" % filespec_in_archive, always=opts.dry_run)
                if install_zip:
                    install_zip.write(filename, filespec_in_archive)
        finally:
            if install_zip:
                install_zip.close()

        return (install_zip and install_zip.filename or None, message)

def change_to_zip_starting_dir():
    for parent_dir_count in range(4):
        child_dir = os.path.join(os.getcwd(), opts.install_pathname)
        if os.path.isdir(child_dir):
            return
        os.chdir("..")
    abort("Please run from inside or above the %s directory" % opts.install_pathname)

def write_file(filename, content):
    if os.path.isfile(filename):
        show("File %s already exists" % os.path.abspath(filename))
        if not opts.force_overwrite:
            return
    try:
        f = file(filename, 'w')
        f.writelines(content)
        show("File created: '%s'" % os.path.abspath(filename))
    finally:
        f.close()

def filenames_to_include(excepting=None, prefix='@'):
    to_include = []
    if opts.include_list:
        to_include = ["%s%s" % (prefix, x) for x in glob("*") if x != excepting]
    return to_include

def get_install_script_details():
    imbedded_version = "%s-%s" % (opts.install_version, cwd_name())
    schema = (opts.install_schema or "MISSING_SCHEMA").upper()
    filename_template = opts.file_template.replace("*", "%s")
    filename = os.path.join(".", filename_template % "")
    return (filename, imbedded_version, schema)

def derive_version():
    if not opts.install_version:
        if cwd_name().isdigit():
            opts.install_version = cwd_parent()
        elif cwd_parent() == opts.install_pathname:
            opts.install_version = cwd_name()
        else:
            abort_not_enough_detail_for_script()
    debug("Determined that the version is %s" % opts.install_version)
    return opts.install_version

def find_best_numbered_dir():
    for n in range(1,100):
        if not os.path.exists(fixpath("./%d/install.sql" % (n))):
            return str(n)
    abort("Unsure where to create installation script. Are you sure you want to be in %s?" % os.getcwd())

def create_and_change_to_installation_directory():

    debug("Currently in directory %s" % os.getcwd())
    version_dir = derive_version()

    if cwd_name().isdigit() and cwd_parent() == version_dir:
        return
    elif cwd_name() == version_dir:
        make_and_change_dir()
    elif cwd_name() == opts.install_pathname:
        make_and_change_dir(version_dir)
    elif cwd_name().startswith("%s" % opts.repo_prefix):
        make_and_change_dir(fixpath("%s/%s" % (opts.install_pathname, version_dir)))
    else:
        abort("Unsure where to put installation file. Are you sure you want to be in %s?" % os.getcwd())

def make_and_change_dir(dir=None):
    if dir:
        if not os.path.exists(dir):
            debug("creating dir %s" % dir)
            os.makedirs(dir)
        debug("changing to dir %s" % dir)
        os.chdir(dir)
    if cwd_name() == opts.install_version:
        make_and_change_dir(find_best_numbered_dir())

def get_expected_installation_location():
    """
    the name or partial name of the subdirectory that contains the installation script (e.g. ssy-3.33.1 or 3.33.1)
    """
    return opts.path_template or get_subdirectory_under_install()

def get_subdirectory_under_install():
    dir = os.getcwd()
    prev_dir = None
    while dir != prev_dir:
        prev_dir = dir
        (dir, path_segment) = os.path.split(dir)
        if dir.endswith(fixpath("/%s" % (opts.install_pathname))):
            return path_segment
    return None

def generate_zip_filespec(script, output_dir):
     (script_path, script_filename) = os.path.split(script)
     zipname = script_path.replace(os.sep, " ").replace(".", " ").strip().replace(" ", "-")
     return fixpath("%s/%s.zip" % (output_dir, zipname))

def abort_not_found(location):
    name = NAME
    abort("""Not sure which installation zip to generate. See '%(name)s --help'.

Did not find an installation script within a subdirectory matching '%(location)s'
"""  % locals())

def abort_not_enough_detail_for_zip():
    name = NAME
    install_path = opts.install_pathname
    abort("""
Not sure which installation zip to generate. See '%(name)s --help'.

Try running in a subdirectory below %(install_path)s, or provide a path segment argument like:

%(name)s 1.0.0
or
%(name)s ssy-3.33.5
"""  % locals())

def abort_not_enough_detail_for_script():
    name = NAME
    cwd = os.getcwd()
    schema = opts.install_schema
    abort("""
Unsure where to create installation script.

Are you sure you want to be in %(cwd)s?"
Or did you forget to add the -n parameter? See '%(name)s --help'.

Example:

%(name)s -I -s %(schema)s -n some-project-0.0.0
"""  % locals())

def build_install_script_boiler_plate_file():
    create_and_change_to_installation_directory()
    (filename, version, schema) = get_install_script_details()
    file_content = install_file_content(version, schema, filenames_to_include(excepting=filename))
    write_file(filename, file_content)

def build_zip_files():
    """
    starting with the current working directory
    look for files of the form: install*.sql

    for each found:
        create a new zip file
        open install sql file and look for lines starting with @
        for each @ file found:
            add that file to the zip file
        close zip file
    """

    debug("CWD %s" % os.getcwd())
    installation_location = get_expected_installation_location()
    if not installation_location:
        abort_not_enough_detail_for_zip()

    change_to_zip_starting_dir()
    (scripts, file_tree) = scan_install_path(".", installation_location, opts.file_template)
    debug("all files encountered:\n   %s" % "\n  ".join(file_tree))
    debug("scripts:\n %s" % "\n ".join(scripts))

    if not scripts:
        abort_not_found(installation_location)

    artifacts_dir = "%s/artifacts" % opts.install_pathname
    if not os.path.exists(artifacts_dir):
        os.makedirs(artifacts_dir)

    for script in scripts:
        (zip_file, message) = generate_zip_file(generate_zip_filespec(script, artifacts_dir), script, file_tree)
        if message:
            show(message)
        if zip_file:
            show(os.path.abspath(zip_file))

# ________________________

if __name__ == "__main__":
# ________________________ 

    opts = read_options()
    if opts.build_install_script:
        build_install_script_boiler_plate_file()
    else:
        build_zip_files()
        
#!/usr/bin/python
# -*- coding: utf-8 -*-
import __builtin__
import bz2
import codecs
import json
import optparse
import os
import pkg_resources
import pysftp
import paramiko
import shutil
import subprocess
import sys
import tarfile
import urllib2
import zipfile
from distutils.version import StrictVersion
from utils import *

if is_windows:
    from platform_windows import *
elif is_mac:
    from platform_mac import *
elif is_linux:
    from platform_linux import *
else:
    print "Unsupported platform."
    sys.exit(1)

# FILE CONTENTS AND STRUCTURE BELOW
# Things to gather up for submission
LOGFILESUBDIRECTORY = 'logs'
NUMBER_OF_PG_LOGS = 20  # Amount of postgres logs to gather - there's one per day usually

DBFILESSUBDIRECTORY = 'dbs'
CONFFILESSUBDIRECTORY = 'config'
SYSTEMINFOSUBDIRECTORY = 'sysinfo'

# Server information
SERVERNAME='ut.filewave.com'
DOWNLOADUSER='fwtech'
DOWNLOADPWD='DOWNLOAD_PASSWORD_HERE'
UPLOADPORT=32000

######### END OF SETTINGS ############

######### SFTP FUNCTIONALITY ##########
def download_sftpfile(customerid, sourcefile):
    # creates an sftp user on the support site by placing a file with the desired username on it on the box
    # create an empty flagfile for upload
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None # won't use known_hosts
    conninfo = {'host': SERVERNAME, 'username': DOWNLOADUSER, 'password': DOWNLOADPWD, 'port': UPLOADPORT, 'cnopts': cnopts}
    # connect to the sftp , and create an account by placing a markerfile ; disconnect from marker account
    try:
        with pysftp.Connection(**conninfo) as userftp:
            with userftp.cd(customerid):
                userftp.get(sourcefile)
                shutil.move(sourcefile, TEMPFILEPATH)
    except paramiko.ssh_exception.SSHException as exc:
        print "\nSSH exception: {0}".format(exc)
        sys.exit(1)
    except :
        print sys.exc_info()[0]
        print "\nCould not connect to {0} on port {1} - please verify this works and try again.".format(SERVERNAME,UPLOADPORT)
        sys.exit(1)
        
######### END OF SFTP FUNCTIONALITY ##########

######### ARCHIVE MANAGEMENT AND CLEANUP FUNCTIONALITY ##########

def parse_commandline():
    global KEEP_SENSITIVE_DATA
    global INSTALL_TARGET_VERSION
    global SOURCEFILE

    usage = 'usage: %prog [options] filename'
    parser = optparse.OptionParser(usage=usage, description='Downloads debug information of a customer and installs it.')
    parser.add_option('-k', '--keep-data', action='store_true', help='do not remove sensitive data (VPP tokens, certificates, passwords,...)')
    # If specified, do not uninstall the current version/install target version.
    parser.add_option('-n', '--no-install', action='store_true', help='do not install the target FileWave version.')
    parser.add_option('-v', '--verbose', action='store_true', help='verbose output')
    (options, args) = parser.parse_args()

    if not args:
        parser.print_help()
        sys.exit(1)

    __builtin__.VERBOSE = options.verbose
    KEEP_SENSITIVE_DATA = options.keep_data
    INSTALL_TARGET_VERSION = not options.no_install
    SOURCEFILE = args[0]

    if KEEP_SENSITIVE_DATA:
        print 'Will keep sensitive data after restoring the database dump.'
    if not INSTALL_TARGET_VERSION:
        print "Local FileWave installation will not be uninstalled. Make sure you're running the correct version."
        print "IMPORTANT: Existing database/configuration files will be lost!"
    if __builtin__.VERBOSE:
        print 'Verbosity on.'


def parse_timestamp(timestamp):
    p = timestamp.split('.')[0].split('-')
    return '{0}-{1}-{2} {3}:{4}'.format(p[0], p[1], p[2], p[4], p[5])


def execute_postgresql_query(sql):
    subprocess_call([psql_command,
                     '-d', 'mdm',
                     '-U', 'django',
                     '-c', sql])


def unpack_data(TEMPFILEPATH, SOURCEFILE):
    # pack it all up and name it in a way that makes sense
    try:
        datafile = tarfile.open(os.path.join(TEMPFILEPATH, SOURCEFILE))
        datafile.extractall(TEMPFILEPATH)
        datafile.close()
    except:
        print sys.exc_info()[0]
        print "Unable to unpack downloaded file. Is there enough space? Aborting ..."
        sys.exit(1)


def download_fwinstaller(fwversion, filewave_package_path):
    if StrictVersion(fwversion) > StrictVersion('10.0.2'):
        url = 'http://fwdl.filewave.com/{0}/{1}'.format(fwversion, filewave_package_name(fwversion))
    else:
        url = 'http://downloads.filewave.com/{0}/{1}'.format(fwversion, filewave_package_name(fwversion))

    if __builtin__.VERBOSE:
        sys.stdout.write('  Downloading: {0} ...  '.format(url))
        sys.stdout.flush()

    resp = urllib2.urlopen(url)
    CHUNK = 16 * 1024
    with open(filewave_package_path, 'wb') as f:
        while True:
            chunk = resp.read(CHUNK)
            if not chunk: break
            f.write(chunk)


def uninstall_filewave():
    try:
        os.listdir(pgdata_dir)
    except OSError:
        print 'No current installation detected, continuing...'
        raise RuntimeError('No current installation detected, continuing...')

    print "\n\nExisting FileWave Server installation detected! Uninstalling...\n"
    unknown_length_status(stop_server, (), "Stopping services...")

    archived_path = unknown_length_status(archive_existing_installation, (), "Archiving existing installation...")
    print "  Archived into:", archived_path
    remove_filewave_packages()

    sys.stdout.write('%-40s  ' % "Wiping config files...")
    sys.stdout.flush()
    for conffile in conffiles:
        if os.path.isfile(conffile):
            os.remove(conffile)
    print "\b\b Success"

    sys.stdout.write('%-40s  ' % "Wiping log files...")
    sys.stdout.flush()
    for logfile in logfiles:
        if os.path.isfile(logfile):
            os.remove(logfile)
    print "\b\b Success"

    unknown_length_status(wipe_existing_installation, (), "Wiping remaining files...")

    print "\nUninstall complete. Starting restore...\n"


def restore_config_files(conffiles):
    # place config files
    # need to check if platform matches original platform
    # for now, just put it into /configfiles
    if OSMATCH:
        sys.stdout.write('%-40s  ' % "Restoring config files...")
        sys.stdout.flush()
        for conffile in conffiles:
            if os.path.isfile(os.path.join(TEMPFILEPATH, 'config', conffile)):
                os.rename(os.path.join(TEMPFILEPATH, 'config', conffile), conffile)
        set_pgdata_ownership()
        print "\b\b Success"
    else:
        print "Non-Matching OS. Moving config files to /captured-config ..."
        captured_config = os.path.join(os.sep, 'captured-config')
        if os.path.isdir(captured_config):
            shutil.rmtree(captured_config)
        shutil.move(os.path.join(TEMPFILEPATH, 'config'), captured_config)


def restore_log_files():
    # place logfiles
    # need to check if platform matches original platform
    # for now, just put it into /logfiles
    progress_bar("Restoring log files")
    captured_logs = os.path.join(os.sep, 'captured-logs')
    if os.path.isdir(captured_logs):
        shutil.rmtree(captured_logs)
    shutil.move(os.path.join(TEMPFILEPATH, 'logs'), captured_logs)
    progress_bar("Restoring log files", 100)


def restore_sysinfo_files():
    # move sysinfo files into visible space
    progress_bar("Restoring system information files")
    captured_sysinfo = os.path.join(os.sep, 'captured-sysinfo')
    if os.path.isdir(captured_sysinfo):
        shutil.rmtree(captured_sysinfo)
    shutil.move(os.path.join(TEMPFILEPATH, 'sysinfo'), captured_sysinfo)
    progress_bar("Restoring system information files", 100)


def restore_sqlite_database(sqlitedbfiles):
    # import the sqlite DBs
    print "Restoring sqlite databases"
    for sqlitedb in sqlitedbfiles:
        sourcefilename = os.path.split(sqlitedb)[1] + ".dump"
        sourcefile = os.path.join(TEMPFILEPATH, 'dbs', sourcefilename)
        sys.stdout.write('%-40s  ' % sourcefilename)
        sys.stdout.flush()
        if not os.path.isfile(sourcefile):
            if os.path.splitext(sqlitedb)[1].lower() == '.bak':
                print "\b\b Not found"
            else:
                print "\b\b Failed!"
                print "Error: The Debug Information File does not contain %s !" % sourcefilename
                raise OSError(2)
        else:
            if os.path.isfile(sqlitedb):
                os.remove(sqlitedb)
            call_sqlite3('"%s" <"%s"' % (sqlitedb, sourcefile))
            print "\b\b Success"


def remove_sqlite_sensitive_data():
    # Clear administrator passwords
    progress_bar("Removing sensitive data from sqlite")
    sql = "UPDATE administrator SET password=NULL;"
    call_sqlite3('"%s" "%s"' % (sqlitedbfiles[0], sql))

    # Set default password of user 'fwadmin' to 'filewave'
    progress_bar("Removing sensitive data from sqlite", 33)
    sql = "UPDATE administrator SET password=X'302d2e08120109140208150e' WHERE shortname='fwadmin';"
    call_sqlite3('"%s" "%s"' % (sqlitedbfiles[0], sql))

    progress_bar("Removing sensitive data from sqlite", 66)
    # Remove MDM, Inventory, Imaging and Engage settings from server, including shared keys.
    sql = "DELETE FROM name_value_pair WHERE " \
          "name='mdm_server_configuration' OR " \
          "name='inventory_server_configuration' OR " \
          "name='imaging_server_configuration' OR " \
          "name='engage_server_configuration';"
    call_sqlite3('"%s" "%s"' % (sqlitedbfiles[0], sql))

    progress_bar("Removing sensitive data from sqlite", 100)


def restore_postgresql_database(os_version):
    # start postgres, import the postgres DB
    progress_bar("Restoring PostgreSQL data")
    if not os.path.isfile(os.path.join(TEMPFILEPATH, 'dbs', 'mdm-sql.dump')):
        if OSMATCH:
            print "Postgres DB was not functional at time of capture."
            print "Restoring raw pg_data folder - good luck!"
            os.rename(os.path.join(TEMPFILEPATH, 'dbs', 'pg_data'), pgdata_dir)
        else:
            print "POSTGRES DUMP NOT IN CAPTURE DATA !!"
            print "THIS DB CANNOT BE RESTORED UNLESS YOU ARE RUNNING THIS ON THE SAME PLATFORM AS %s " % os_version
            print "ABORTING NOW"
            sys.exit(1)

    progress_bar("Restoring PostgreSQL data", 100*1/6)
    start_postgresql()

    # drop the mdm DB and create a new one
    progress_bar("Restoring PostgreSQL data", 100*2/6)
    subprocess_call([psql_command,
                     '-d', 'postgres',
                     '-U', postgres_admin,
                     '-c', 'DROP DATABASE mdm;'])

    progress_bar("Restoring PostgreSQL data", 100*3/6)
    subprocess_call([psql_command,
                     '-d', 'postgres',
                     '-U', postgres_admin,
                     '-c', "CREATE DATABASE mdm OWNER django TEMPLATE=template0 ENCODING='UTF8';"])

    # restore the backup
    progress_bar("Restoring PostgreSQL data", 100*4/6)
    subprocess_call([psql_command,
                    '-d', 'mdm',
                    '-U', postgres_admin,
                    '-f', os.path.join(TEMPFILEPATH, 'dbs', 'mdm-sql.dump'),
                    '-o', os.path.join(os.sep, 'downloader-psql-restore-log')])

    #restore access priviledges on the DB in case that is missing from the dump file
    progress_bar("Restoring PostgreSQL data", 100*5/6)
    execute_postgresql_query('GRANT ALL ON SCHEMA public TO public;')

    progress_bar("Restoring PostgreSQL data", 100)


def remove_postgresql_sensitive_data():
    current_step = 0
    steps = 5
    progress_bar("Removing sensitive data from PostgreSQL")

    if not requires_sqlite:
        steps += 3
        # Clear administrator passwords
        execute_postgresql_query("UPDATE admin.administrator SET password=NULL;")
        current_step += 1

        # Set default password of user 'fwadmin' to 'filewave'
        progress_bar("Removing sensitive data from PostgreSQL", 100*current_step/steps)
        execute_postgresql_query("UPDATE admin.administrator SET password=DECODE('302d2e08120109140208150e', 'hex') WHERE shortname='fwadmin';")
        current_step += 1

        # Remove MDM, Inventory, Imaging and Engage settings from server, including shared keys.
        progress_bar("Removing sensitive data from PostgreSQL", 100*current_step/steps)
        execute_postgresql_query("DELETE FROM admin.name_value_pair WHERE "
                                 "name='mdm_server_configuration' OR "
                                 "name='inventory_server_configuration' OR "
                                 "name='imaging_server_configuration' OR "
                                 "name='engage_server_configuration';")
        current_step += 1

    # Remove MDM and Engage shared key from Django
    progress_bar("Removing sensitive data from PostgreSQL", 100 * current_step / steps)
    execute_postgresql_query("DELETE FROM ios_preferences WHERE "
                             "key='shared_key' OR "
                             "key='engage_server_settings' OR "
                             "key='gcm_settings' OR "
                             "key='gcm_status';")
    current_step += 1

    # Remove inventory shared key from Django
    progress_bar("Removing sensitive data from PostgreSQL", 100 * current_step / steps)
    execute_postgresql_query("DELETE FROM inventory_preferences WHERE key='shared_key';")
    current_step += 1

    # Remove VPP tokens...
    progress_bar("Removing sensitive data from PostgreSQL", 100 * current_step / steps)
    try:
        execute_postgresql_query("CREATE OR REPLACE FUNCTION clear_VPP_one () RETURNS text AS '\n"
                                 "  DECLARE\n"
                                 "    text_output TEXT :=''Cleared VPP Token data.'';\n"
                                 "    vpp_data ios_organization%ROWTYPE;\n"
                                 "      count INTEGER :=0;\n"
                                 "  BEGIN\n"
                                 "    FOR vpp_data IN SELECT * FROM ios_organization LOOP\n"
                                 "      UPDATE ios_organization SET token = count WHERE token = vpp_data.token;\n"
                                 "        count = count + 1;\n"
                                 "    END LOOP;\n"
                                 "    RETURN text_output;\n"
                                 "  END;\n"
                                 "' LANGUAGE 'plpgsql';")
        execute_postgresql_query("SELECT clear_VPP_one();")
        execute_postgresql_query("DROP FUNCTION IF EXISTS clear_VPP_one();")
    except OSError:
        pass
    current_step += 1

    progress_bar("Removing sensitive data from PostgreSQL", 100 * current_step / steps)
    try:
        execute_postgresql_query("CREATE OR REPLACE FUNCTION clear_VPP_two () RETURNS text AS '\n"
                                 "  DECLARE\n"
                                 "    text_output TEXT :=''Cleared VPP Token data.'';\n"
                                 "    vpp_data apple_vpp_organization%ROWTYPE;\n"
                                 "    count INTEGER :=0;\n"
                                 "  BEGIN\n"
                                 "    FOR vpp_data IN SELECT * FROM apple_vpp_organization LOOP\n"
                                 "      UPDATE apple_vpp_organization SET token = count WHERE token = vpp_data.token;\n"
                                 "        count = count + 1;\n"
                                 "    END LOOP;\n"
                                 "    RETURN text_output;\n"
                                 "  END;\n"
                                 "' LANGUAGE 'plpgsql';")
        execute_postgresql_query("SELECT clear_VPP_two();")
        execute_postgresql_query("DROP FUNCTION IF EXISTS clear_VPP_two();")
    except OSError:
        pass
    current_step += 1

    # Clear VPP and DEP token data
    progress_bar("Removing sensitive data from PostgreSQL", 100 * current_step / steps)
    try:
        execute_postgresql_query("CREATE OR REPLACE FUNCTION clear_VPP_DEP () RETURNS text AS '\n"
                                 "  DECLARE\n"
                                 "    text_output TEXT :=''Cleared VPP and DEP Token data.'';\n"
                                 "    vpp_data apple_vpp_organization%ROWTYPE;\n"
                                 "    dep_data apple_dep_account%ROWTYPE;\n"
                                 "    count INTEGER :=0;\n"
                                 "  BEGIN\n"
                                 "    FOR vpp_data IN SELECT * FROM apple_vpp_organization LOOP\n"
                                 "       UPDATE apple_vpp_organization SET token = count WHERE token = vpp_data.token;\n"
                                 "       count = count + 1;\n"
                                 "    END LOOP;\n"
                                 "    count = 0;\n"
                                 "    FOR dep_data IN SELECT * FROM apple_dep_account LOOP\n"
                                 "       UPDATE apple_dep_account SET _token = count WHERE _token = dep_data._token;\n"
                                 "       UPDATE apple_dep_account SET cursor = count WHERE cursor = dep_data.cursor;\n"
                                 "       count = count + 1;\n"
                                 "    END LOOP;\n"
                                 "    RETURN text_output;\n"
                                 "  END;\n"
                                 "' LANGUAGE 'plpgsql';")
        execute_postgresql_query("SELECT clear_VPP_DEP();")
        execute_postgresql_query("DROP FUNCTION IF EXISTS clear_VPP_DEP();")
    except OSError:
        pass
    current_step += 1

    progress_bar("Removing sensitive data from PostgreSQL", 100)


######### MAIN FUNCTION ###########
parse_commandline()

print "FileWave Debug Information Downloader"
# check for root rights
if not is_root_user():
    print("Please run this as root/administrator.")
    sys.exit(1)

# if there's less than 500 MB free on / , we'll give up at this point.
if get_free_disk_space() < 500000:
    print ("Less than 500 MB space available on / filesystem. Free space and try again - aborting!")
    sys.exit(1)

# determine details about the caputred data to be downloaded
try:
    customerid, fwversion, osversion, originaltimestamp = SOURCEFILE.split('-',3)
    customerid_readable = customerid
    if customerid_readable == '0110010101110110011000010000eval':
        customerid_readable = '<Evaluation license>'
    originaltimestamp = parse_timestamp(originaltimestamp)
except IndexError:
    print 'Invalid file name.'
    sys.exit(1)

print "----------------------------------------------------"
print "      Customer ID:", customerid_readable
print " FileWave Version:", fwversion
print "       OS Version:", osversion
print "Capture Timestamp:", originaltimestamp
print "----------------------------------------------------"
print

requires_sqlite = StrictVersion(fwversion) < StrictVersion('10.9')

try:
    if os.path.exists(TEMPFILEPATH):
        shutil.rmtree(TEMPFILEPATH)
    os.makedirs(TEMPFILEPATH)
except:
    print "Could not create temporary directory in %s. Aborting!" % TEMPFILEPATH
    sys.exit(1)

# Download the archive
unknown_length_status(download_sftpfile, (customerid, SOURCEFILE), "Downloading Debug Information File...")
# unpack
unknown_length_status(unpack_data, (TEMPFILEPATH, SOURCEFILE), "Unpacking Debug Information File...")
# get the installer
if INSTALL_TARGET_VERSION:
    filewave_package_path = os.path.join(TEMPFILEPATH, filewave_package_name(fwversion))
    unknown_length_status(download_fwinstaller, (fwversion, filewave_package_path), "Downloading FileWave %s..." % fwversion)

    # check for existing fwxserver installation, if there is one archive and uninstall
    try:
        uninstall_filewave()
    except RuntimeError:
        pass

    # unpack the installer(s)
    install_filewave_package(fwversion, filewave_package_path)
else:
    unknown_length_status(stop_server, (), "Stopping server...")

# decide whether it's an os match or not
OSMATCH = sourcefile_matches_os_version(osversion)

# restore the archive
restore_config_files(conffiles)
restore_log_files()
restore_sysinfo_files()

if requires_sqlite:
    restore_sqlite_database(sqlitedbfiles)
    if not KEEP_SENSITIVE_DATA:
        remove_sqlite_sensitive_data()

restore_postgresql_database(osversion)
if not KEEP_SENSITIVE_DATA:
    remove_postgresql_sensitive_data()

unknown_length_status(stop_postgresql, (), "Stopping PostgreSQL...")
unknown_length_status(set_local_mdm_configuration, (), "Configuring local MDM host...")
unknown_length_status(stop_server, (), "Shutting down server...")

# display notification of completion
print
print "%s has been successfully restored." % SOURCEFILE
print "Server is shut down at the moment. Start it using 'fwcontrol server start'."
print "Debug Data is located in the {0}captured-* folders".format(os.path.abspath(os.sep))

# cleanup
shutil.rmtree(os.path.join(os.sep,'captured-downloads'), ignore_errors=True)
shutil.move(TEMPFILEPATH, os.path.join(os.sep,'captured-downloads'))

print
print "Success!"

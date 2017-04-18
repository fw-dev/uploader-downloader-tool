# -*- coding: utf-8 -*-
import ctypes
import getpass
import os
import shutil
import subprocess
import sys
import time
import zipfile
from distutils.version import StrictVersion

import pythoncom
import pywintypes
import win32api
from utils import *
from win32com.shell import shell

try:
    filewave_dir = os.path.join(os.environ['PROGRAMFILES(x86)'], 'FileWave')
except KeyError:
    filewave_dir = os.path.join(os.environ['PROGRAMFILES'], 'FileWave')

pgdata_dir = os.path.join(os.environ['PROGRAMDATA'], 'FileWave\\FWServer\\DB\\pg_data')

logfiles = [os.path.join(os.environ['PROGRAMDATA'], 'FileWave\\FWServer\\fwxserver.log'),
            os.path.join(os.environ['PROGRAMDATA'], 'FileWave\\FWServer\\fwxadmin.log'),
            os.path.join(os.environ['PROGRAMDATA'], 'FileWave\\FWServer\\fwxother.log'),
            os.path.join(os.environ['PROGRAMDATA'], 'FileWave\\FWServer\\fwldap.log'),
            os.path.join(filewave_dir, 'apache\\logs\\access.log'),
            os.path.join(filewave_dir, 'apache\\logs\\error.log'),
            os.path.join(os.environ['PROGRAMDATA'], 'FileWave\\FWServer\\log\\filewave_django.log'),
            os.path.join(os.environ['PROGRAMDATA'], 'FileWave\\FWServer\\log\\request_errors.log'),
            os.path.join(os.environ['PROGRAMDATA'], 'FileWave\\FWServer\\log\\sql.log'),
            os.path.join(filewave_dir, 'log\\fwscheduler.log')
           ]

conffiles = [os.path.join(filewave_dir, 'apache\\conf\\mdm_auth.conf'),
             os.path.join(filewave_dir, 'apache\\conf\\httpd.conf'),
             os.path.join(filewave_dir, 'apache\\conf\\httpd_custom.conf'),
             os.path.join(filewave_dir, 'django\\filewave\\settings.py'),
             os.path.join(filewave_dir, 'django\\filewave\\settings_custom.py'),
             os.path.join(os.environ['PROGRAMDATA'], 'FileWave\\FWServer\\conf\\user_postgresql.conf'),
             os.path.join(pgdata_dir, 'postgresql.conf'),
             os.path.join(os.environ['PROGRAMDATA'], 'FileWave\\FWServer\\fwxcodes')
            ]

sysinfofiles = []

sqlitedbfiles = [os.path.join(os.environ['PROGRAMDATA'], 'FileWave\\FWServer\\DB\\admin.sqlite'),
                 os.path.join(os.environ['PROGRAMDATA'], 'FileWave\\FWServer\\DB\\committed.sqlite'),
                 os.path.join(os.environ['PROGRAMDATA'], 'FileWave\\FWServer\\DB\\server.sqlite'),
                 os.path.join(os.environ['PROGRAMDATA'], 'FileWave\\FWServer\\DB\\ldap.sqlite'),
                 os.path.join(os.environ['PROGRAMDATA'], 'FileWave\\FWServer\\DB\\admin.sqlite.bak'),
                 os.path.join(os.environ['PROGRAMDATA'], 'FileWave\\FWServer\\DB\\server.sqlite.bak'),
                 os.path.join(os.environ['PROGRAMDATA'], 'FileWave\\FWServer\\DB\\ldap.sqlite.bak')
                ]

psql_command = os.path.join(filewave_dir, 'postgresql\\bin\\psql.exe')
postgres_admin = getpass.getuser()

fwcontrol = os.path.join(filewave_dir, 'bin\\fwcontrol.cmd')

#local file storage
TEMPFILEPATH = 'C:\\Windows\\Temp\\fwdownloader\\'


def archive_existing_installation():
    archive_path = 'C:\\fwxserver-archive-' + time.strftime("%Y-%m-%d--%H-%M", time.gmtime())
    os.mkdir(archive_path)

    archived_program_files = os.path.join(archive_path, 'Program Files')
    os.mkdir(archived_program_files)
    subprocess_call(['xcopy', '/E', '/I', '/H', '/Y', '/Q',
                     filewave_dir, archived_program_files])

    archived_program_data = os.path.join(archive_path, 'ProgramData')
    os.mkdir(archived_program_data)
    subprocess_call(['xcopy', '/E', '/I', '/H', '/Y', '/Q',
                     os.path.join(os.environ['PROGRAMDATA'], 'FileWave'), archived_program_data])

    return archive_path


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def call_sqlite3(args):
    cmdline = resource_path('sqlite3.exe') + ' ' + args
    subprocess_call(cmdline, shell=True)


def filewave_package_name(fwversion):
    return 'FileWave_Windows_{0}.zip'.format(fwversion)


def get_free_disk_space():
    free_bytes = ctypes.c_ulonglong(0)
    ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(u'c:\\'), None, None, ctypes.pointer(free_bytes))
    return free_bytes


def install_filewave_package(fwversion, filewave_package_path):
    sys.stdout.write('%-40s  ' % "Uncompressing FileWave %s" % fwversion)
    sys.stdout.flush()
    installer_zip=zipfile.ZipFile(filewave_package_path, 'r')
    installer_zip.extractall(TEMPFILEPATH)
    print "\b\b Success"

    #run the installer(s)
    if StrictVersion(fwversion) < StrictVersion('10.9'):
        server_msi = os.path.join(TEMPFILEPATH, 'FileWaveServer.msi')
        # shell=True is required because msi files cannot be executed directly
        unknown_length_status(subprocess_call, ([server_msi, '/quiet', '/passive'], True), "Installing FileWave Server %s" % fwversion)

        mdm_exe = os.path.join(TEMPFILEPATH, 'FileWaveMDM.exe')
        unknown_length_status(subprocess_call, ([mdm_exe, '/exenoupdates', '/exenoui'],), "Installing FileWave MDM %s" % fwversion)
    else:
        server_exe = os.path.join(TEMPFILEPATH, 'FileWaveServer.exe')
        unknown_length_status(subprocess_call, ([server_exe, '/exenoupdates', '/exenoui'],), "Installing FileWave Server %s" % fwversion)

    # shell=True is required because msi files cannot be executed directly
    admin_msi = os.path.join(TEMPFILEPATH, 'FileWaveAdmin.msi')
    unknown_length_status(subprocess_call, ([admin_msi, '/quiet', '/passive'], True), "Installing FileWave Admin %s" % fwversion)

    #shut the server down
    unknown_length_status(stop_server, (), "Stopping server...")

def is_root_user():
    return shell.IsUserAnAdmin()


def remove_filewave_packages():
    progress_bar("Uninstalling...")
    subprocess_call('wmic product where name="FileWave Client" call uninstall /nointeractive')

    progress_bar("Uninstalling...", 100*1/6)
    subprocess_call('wmic product where name="FileWave Admin" call uninstall /nointeractive')

    progress_bar("Uninstalling...", 100*2/6)
    subprocess_call('wmic product where name="FileWave Booster" call uninstall /nointeractive')

    progress_bar("Uninstalling...", 100*3/6)
    subprocess_call('wmic product where name="FileWave MDM" call uninstall /nointeractive')

    progress_bar("Uninstalling...", 100*4/6)
    subprocess_call('wmic product where name="FileWave Unified Server" call uninstall /nointeractive')

    progress_bar("Uninstalling...", 100*5/6)
    subprocess_call('wmic product where name="FileWave Server" call uninstall /nointeractive')

    progress_bar("Uninstalling...", 100)


def set_local_mdm_configuration():
    subprocess_call_ignoreerror([fwcontrol, 'server', 'setdbconn', '127.0.0.1'])


def set_pgdata_ownership():
    pass


def sourcefile_matches_os_version(osversion):
    return 'Windows' in osversion


def start_postgresql():
    subprocess_call(['net','start','FileWave MDM PostgreSQL'])


def stop_postgresql():
    subprocess_call(['net','stop','FileWave MDM PostgreSQL'])


def stop_server():
    time.sleep(3)
    subprocess_call_ignoreerror(['net', 'stop', 'FileWave UltraVNC Server'])
    subprocess_call_ignoreerror(['net', 'stop', 'FileWave Client'])
    subprocess_call_ignoreerror(['net', 'stop', 'FileWave Booster'])
    subprocess_call_ignoreerror(['net', 'stop', 'FileWave Admin Service'])
    subprocess_call_ignoreerror(['net', 'stop', 'FileWave Server Service'])
    subprocess_call_ignoreerror(['net', 'stop', 'FileWave Scheduler'])
    subprocess_call_ignoreerror(['net', 'stop', 'FileWave MDM Apache'])
    subprocess_call_ignoreerror(['net', 'stop', 'FileWave MDM PostgreSQL'])
    subprocess_call_ignoreerror(['net', 'stop', 'FileWave LDAP'])
    time.sleep(3)
    # Just to be sure
    subprocess_call_ignoreerror(['net', 'stop', 'FileWave Server Service'])


def wipe_existing_installation():
    try:
        shutil.rmtree(filewave_dir)
    except OSError:
        pass

    try:
        shutil.rmtree(os.path.join(os.environ['PROGRAMDATA'], 'FileWave'))
    except OSError:
        pass

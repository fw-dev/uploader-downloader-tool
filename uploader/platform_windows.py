# -*- coding: utf-8 -*-
import ctypes
import os
import subprocess
import sys
from utils import *

try:
    filewave_dir = os.path.join(os.environ['PROGRAMFILES(x86)'],'FileWave')
except KeyError:
    filewave_dir = os.path.join(os.environ['PROGRAMFILES'],'FileWave')

pgdata_dir = os.path.join(os.environ['PROGRAMDATA'], 'FileWave\\FWServer\\DB\\pg_data')

logfiles=[os.path.join(os.environ['PROGRAMDATA'], 'FileWave\\FWServer\\fwxserver.log'),
          os.path.join(os.environ['PROGRAMDATA'], 'FileWave\\FWServer\\fwxadmin.log'),
          os.path.join(os.environ['PROGRAMDATA'], 'FileWave\\FWServer\\fwxother.log'),
          os.path.join(os.environ['PROGRAMDATA'], 'FileWave\\FWServer\\fwldap.log'),
          os.path.join(filewave_dir,'apache\\logs\\access.log'),
          os.path.join(filewave_dir,'apache\\logs\\error.log'),
          os.path.join(os.environ['PROGRAMDATA'], 'FileWave\\FWServer\\log\\filewave_django.log'),
          os.path.join(os.environ['PROGRAMDATA'], 'FileWave\\FWServer\\log\\request_errors.log'),
          os.path.join(os.environ['PROGRAMDATA'], 'FileWave\\FWServer\\log\\sql.log'),
          os.path.join(filewave_dir,'log\\fwscheduler.log')
          ]

conffiles=[os.path.join(filewave_dir,'apache\\conf\\mdm_auth.conf'),
          os.path.join(filewave_dir,'apache\\conf\\httpd.conf'),
          os.path.join(filewave_dir,'apache\\conf\\httpd_custom.conf'),
          os.path.join(filewave_dir,'django\\filewave\\settings.py'),
          os.path.join(filewave_dir,'django\\filewave\\settings_custom.py'),
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

sqlitedbbakfiles = [ os.path.join(os.environ['PROGRAMDATA'], 'FileWave\\FWServer\\DB\\admin.sqlite.bak'),
                 os.path.join(os.environ['PROGRAMDATA'], 'FileWave\\FWServer\\DB\\server.sqlite.bak'),
                 os.path.join(os.environ['PROGRAMDATA'], 'FileWave\\FWServer\\DB\\ldap.sqlite.bak')
		]

pglogs_dir = os.path.join(pgdata_dir, 'pg_log')
pgdump_command = os.path.join(filewave_dir,'postgresql\\bin\\pg_dump.exe')
copy_pgdata_command = 'xcopy /E /I /H /Y /Q "{}" "%s"'.format(pgdata_dir)

fwxserver = os.path.join(filewave_dir,'fwxserver.exe')
try:
    os.stat(fwxserver)
except OSError:
    fwxserver = os.path.join(filewave_dir,'bin\\fwxserver.exe')

#local file storage
TEMPFILEPATH='C:\\Windows\\Temp\\fwuploader\\'
LICFILE=os.path.join(os.environ['PROGRAMDATA'], 'FileWave\\FWServer\\fwxcodes')
DATAFILEPATH='C:\\Windows\\Temp\\'


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
    subprocess.call(cmdline, shell=True)

def gather_platform_data(progress_bar, infofilelist, directory):
    #get list of installed software
    subprocess.call('wmic product list > "%s"' % os.path.join(directory,"installed_software.txt"),shell=True)

    #get system logfile
    subprocess.call('wevtutil epl System "%s"' % os.path.join(directory,"system_log.txt"),shell=True)

    #get system information
    subprocess.call('systeminfo >"%s"' % os.path.join(directory,"system_info.txt"),shell=True)
    progress_bar("Gathering system information",50)

    #get network information
    subprocess.call('route print >"%s"' % os.path.join(directory,"routes.txt"),shell=True)
    subprocess.call('ipconfig /all >"%s"' % os.path.join(directory,"ifconfig.txt"),shell=True)
    progress_bar("Gathering system information",75)

    #get disk space, running processes snapshot etc.
    subprocess.call('tasklist /V >"%s"' % os.path.join(directory,"processes.txt"),shell=True)
    subprocess.call('wmic LogicalDisk Where DriveType="3" Get DeviceID,FreeSpace >"%s"' % os.path.join(directory,"diskspace.txt"),shell=True)

def get_os_info():
    osinfo = check_output(['systeminfo'])
    osinfo = osinfo.split('\r')
    for line in osinfo:
        if "OS Name:" in line:
            osinfo = line.replace('OS Name:','')
    osinfo = osinfo.replace('\n','')
    osinfo = osinfo.replace(' ','')
    osinfo = osinfo.replace('Microsoft','')
    return osinfo

def is_postgresql_running():
    return 'postgres.exe' in check_output(['tasklist.exe','/v'])

def start_postgresql():
    subprocess.call('net start "FileWave MDM PostgreSQL"',shell=True)

def get_free_disk_space():
    free_bytes = ctypes.c_ulonglong(0)
    ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(u'c:\\'), None, None, ctypes.pointer(free_bytes))
    return free_bytes

def copy_to_clipboard(text):
    subprocess.call('echo "%s" | clip' % text, shell=True)

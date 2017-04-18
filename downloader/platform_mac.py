# -*- coding: utf-8 -*-
import os
import shutil
import subprocess
import sys
import time
from distutils.version import StrictVersion
from utils import *

pgdata_dir = '/fwxserver/DB/pg_data'

logfiles = ['/private/var/log/fwxserver.log',
            '/private/var/log/fwxadmin.log',
            '/private/var/log/fwxother.log',
            '/private/var/log/fwldap.log',
            '/usr/local/filewave/apache/logs/access_log',
            '/usr/local/filewave/apache/logs/error_log',
            '/usr/local/filewave/log/filewave_django.log',
            '/usr/local/filewave/log/request_errors.log',
            '/usr/local/filewave/log/sql.log',
            '/usr/local/filewave/log/py_scheduler.log'
           ]

conffiles = ['/usr/local/etc/fwxserver.conf',
             '/Library/Preferences/com.filewave.fwxserver.plist',
             '/Library/LaunchDaemons/com.filewave.fwxserver-admin.plist',
             '/Library/LaunchDaemons/com.filewave.fwxserver-server.plist',
             '/Library/LaunchDaemons/com.filewave.fwxserver-ldap.plist',
             '/Library/LaunchDaemons/com.filewave.fwxserver-apache.plist',
             '/Library/LaunchDaemons/com.filewave.fwxserver-scheduler.plist',
             '/Library/LaunchDaemons/com.filewave.postgresql.plist',
             '/usr/local/filewave/apache/conf/mdm_auth.conf',
             '/usr/local/filewave/apache/conf/httpd.conf',
             '/usr/local/filewave/apache/conf/httpd_custom.conf',
             '/usr/local/filewave/django/filewave/settings.py',
             '/usr/local/filewave/django/filewave/settings_custom.py',
             '/usr/local/filewave/postgresql/conf/user_postgresql.conf',
             os.path.join(pgdata_dir, 'postgresql.conf'),
             '/usr/local/etc/fwxcodes'
            ]

sysinfofiles = ['/var/log/system.log',
                '/var/log/install.log',
                '/Library/Preferences/Systemconfiguration/*',
                '/etc/resolv.conf',
                '/System/Library/CoreServices/SystemVersion.plist',
               ]

sqlitedbfiles=['/fwxserver/DB/admin.sqlite',
               '/fwxserver/DB/committed.sqlite',
               '/fwxserver/DB/server.sqlite',
               '/fwxserver/DB/ldap.sqlite',
               '/fwxserver/DB/admin.sqlite.bak',
               '/fwxserver/DB/server.sqlite.bak',
               '/fwxserver/DB/ldap.sqlite.bak'
              ]

psql_command = '/usr/local/filewave/postgresql/bin/psql'
postgres_admin = 'postgres'

fwcontrol = '/sbin/fwcontrol'
try:
    os.stat(fwcontrol)
except OSError:
    fwcontrol = '/usr/local/bin/fwcontrol'

#local file storage
TEMPFILEPATH = '/private/tmp/fwdownloader/'

def archive_existing_installation():
    archive_path = '/fwxserver-archive-' + time.strftime("%Y-%m-%d--%H-%M", time.gmtime())
    os.mkdir(archive_path)
    for path in ['/fwxserver', '/usr/local/etc', '/usr/local/filewave']:
        target = os.path.dirname(archive_path + path)
        try:
            subprocess_call(['/bin/mkdir', '-p', target])
        except OSError:
            pass
        subprocess_call(['/bin/cp', '-a', path, target])

    return archive_path


def call_sqlite3(args):
    cmdline = '/usr/bin/sqlite3 {0}'.format(args)
    subprocess_call(cmdline, shell=True)


def filewave_package_name(fwversion):
    if StrictVersion(fwversion) >= StrictVersion('11.2.0'):
        platform = 'macOS'
    else:
        platform = 'OSX'
    return 'FileWave_{0}_{1}.dmg'.format(platform, fwversion)


def get_free_disk_space():
    free_space = os.statvfs('/')
    return (free_space.f_bavail * free_space.f_frsize) / 1024


def install_filewave_package(fwversion, filewave_package_path):
    mountpoint = os.path.join(TEMPFILEPATH, "FILEWAVE")
    adminpkg = os.path.join(mountpoint, 'FileWave Admin.pkg')
    serverpkg = os.path.join(mountpoint, 'FileWave Server.pkg')
    os.mkdir(mountpoint)
    sys.stdout.write('%-40s  ' % "Mounting Image...")
    sys.stdout.flush()
    subprocess_call(['/usr/bin/hdiutil',
                     'attach',
                     '-mountpoint', mountpoint,
                     '-nobrowse',
                     '-quiet',
                     filewave_package_path])
    print "\b\b Success"
    sys.stdout.write('%-40s  ' % "Installing FileWave Admin...")
    sys.stdout.flush()
    subprocess_call(['/usr/sbin/installer',
                     '-pkg',
                     adminpkg,
                     '-target', '/'])
    print "\b\b Success"
    sys.stdout.write('%-40s  ' % "Installing FileWave Server...")
    sys.stdout.flush()
    subprocess_call(['/usr/sbin/installer',
                     '-pkg', serverpkg,
                     '-target', '/'])
    print "\b\b Success"
    sys.stdout.write('%-40s  ' % "Unmounting Image...")
    sys.stdout.flush()
    subprocess_call(['/sbin/umount', mountpoint])
    print "\b\b Success"

    #shut the server down
    sys.stdout.write('%-40s  ' % "Stopping server...")
    stop_server()

    try:
        subprocess_call(['/usr/bin/killall', 'fwsu'])
    except OSError:
        pass

    print "\b\b Success"


def is_root_user():
    return os.geteuid()==0


def remove_filewave_packages():
    progress_bar("Uninstalling...")
    shutil.rmtree('/Library/Frameworks/FileWaveCore.framework')

    progress_bar("Uninstalling...", 25)
    os.remove('/usr/local/sbin/fwxserver')

    progress_bar("Uninstalling...", 50)
    os.remove('/usr/local/sbin/fwldap')

    progress_bar("Uninstalling...", 75)
    os.remove(fwcontrol)

    progress_bar("Uninstalling...", 100)


def set_local_mdm_configuration():
    subprocess_call([fwcontrol, 'server', 'setdbconn', '/tmp'])


def set_pgdata_ownership():
    subprocess_call(['/usr/sbin/chown', '-R', 'postgres', pgdata_dir])


def sourcefile_matches_os_version(osversion):
    return 'Mac' in osversion


def start_postgresql():
    subprocess_call([fwcontrol, 'postgres', 'start'])
    time.sleep(3)


def stop_postgresql():
    subprocess_call([fwcontrol, 'postgres', 'stop'])
    time.sleep(3)


def stop_server():
    subprocess_call([fwcontrol, 'server', 'stop'])
    subprocess_call([fwcontrol, 'booster', 'stop'])
    subprocess_call([fwcontrol, 'client', 'stop'])


def wipe_existing_installation():
    for path in ['/fwxserver', '/usr/local/etc', '/usr/local/filewave']:
        try:
            subprocess_call(['/bin/rm', '-Rf', path])
        except OSError:
            pass

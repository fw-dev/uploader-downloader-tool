# -*- coding: utf-8 -*-
import os
import errno
import subprocess
import sys
import time
import zipfile
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
             '/usr/local/filewave/apache/conf/mdm_auth.conf',
             '/usr/local/filewave/apache/conf/httpd.conf',
             '/usr/local/filewave/apache/conf/httpd_custom.conf',
             '/usr/local/filewave/django/filewave/settings.py',
             '/usr/local/filewave/django/filewave/settings_custom.py',
             '/usr/local/filewave/postgresql/conf/user_postgresql.conf',
             os.path.join(pgdata_dir, 'postgresql.conf'),
             '/etc/init.d/fw-mdm-server',
             '/etc/inid.d/fw-server',
             '/usr/local/etc/fwxcodes'
            ]

sysinfofiles = ['/var/log/messages',
                '/var/log/dmesg',
                '/etc/resolv.conf',
                '/var/log/yum.log',
                '/etc/selinux/config'
               ]

sqlitedbfiles = ['/fwxserver/DB/admin.sqlite',
                 '/fwxserver/DB/committed.sqlite',
                 '/fwxserver/DB/server.sqlite',
                 '/fwxserver/DB/ldap.sqlite',
                 '/fwxserver/DB/admin.sqlite.bak',
                 '/fwxserver/DB/server.sqlite.bak',
                 '/fwxserver/DB/ldap.sqlite.bak'
                ]

psql_command = '/usr/local/filewave/postgresql/bin/psql'
postgres_admin = 'postgres'

fwcontrol = '/usr/local/bin/fwcontrol'
try:
    os.stat(fwcontrol)
except OSError:
    fwcontrol = '/usr/local/bin/fwcontrol-server'


#local file storage
TEMPFILEPATH = '/tmp/fwdownloader/'


def archive_existing_installation():
    archive_path = '/fwxserver-archive-' + time.strftime("%Y-%m-%d--%H-%M", time.gmtime())
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
    return 'FileWave_Linux_{0}.zip'.format(fwversion)


def get_free_disk_space():
    free_space = os.statvfs('/')
    return (free_space.f_bavail * free_space.f_frsize) / 1024


def install_filewave_package(fwversion, filewave_package_path):
    unzip = lambda file, targetdir: zipfile.ZipFile(file, 'r').extractall(targetdir)
    unknown_length_status(unzip, (filewave_package_path, TEMPFILEPATH), "Uncompressing FileWave {0}".format(fwversion))

    # run the installer(s)
    yum_install = lambda rpm: subprocess_call(['/usr/bin/yum', 'install', '--nogpgcheck', '-y', rpm])
    fwxserver_rpm = 'fwxserver-{0}-1.0.x86_64.rpm'.format(fwversion)
    unknown_length_status(yum_install, (os.path.join(TEMPFILEPATH, fwxserver_rpm),), "Installing fwxserver {0}".format(fwversion))

    try:
        subprocess_call(['/usr/bin/killall', '-q', 'fwsu'])
    except OSError:
        pass

    try:
        fw_mdm_server_rpm = 'fw-mdm-server-{0}-1.0.x86_64.rpm'.format(fwversion)
        fw_mdm_server_rpm_path = os.path.join(TEMPFILEPATH, fw_mdm_server_rpm)
        os.stat(fw_mdm_server_rpm_path)
        unknown_length_status(yum_install, (os.path.join(TEMPFILEPATH, fw_mdm_server_rpm_path),), "Installing fw-mdm-server {0}".format(fwversion))
    except OSError:
        pass

    # shut the server down
    unknown_length_status(stop_server, (), "Stopping server...")


def is_root_user():
    return os.geteuid()==0


def remove_filewave_packages():
    progress_bar("Uninstalling...")
    subprocess_call(['/bin/rpm', '-e', 'fwxserver'])

    try:
        progress_bar("Uninstalling...", 50)
        subprocess_call(['/bin/rpm', '-e', 'fw-mdm-server'])
    except OSError:
        pass

    progress_bar("Uninstalling...", 100)


def set_local_mdm_configuration():
    subprocess_call([fwcontrol, 'server', 'setdbconn', '/tmp'])


def set_pgdata_ownership():
    subprocess_call(['/bin/chown', '-R', 'postgres', pgdata_dir])


def sourcefile_matches_os_version(osversion):
    return 'CentOS' in osversion


def start_postgresql():
    subprocess_call(['su',
                     'postgres',
                     '-c',
                     'cd / ; /usr/local/filewave/postgresql/bin/pg_ctl start -w -t 10 -D "{0}"'.format(pgdata_dir)
                    ])
    time.sleep(3)


def stop_postgresql():
    subprocess_call(['su',
                     'postgres',
                     '-c',
                     'cd / ; /usr/local/filewave/postgresql/bin/pg_ctl stop -w -t 10 -D "{0}" -s'.format(pgdata_dir)
                    ])


def stop_server():
    try:
        subprocess_call([fwcontrol, 'server', 'stop'])
    except OSError as exc:
        if exc.errno != errno.ENOENT:
            raise
    try:
        subprocess_call([fwcontrol, 'booster', 'stop'])
    except OSError as exc:
        if exc.errno != errno.ENOENT:
            raise
    time.sleep(3)


def wipe_existing_installation():
    for path in ['/fwxserver', '/usr/local/etc', '/usr/local/filewave']:
        try:
            subprocess_call(['/bin/rm', '-Rf', path])
        except OSError:
            pass

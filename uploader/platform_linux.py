# -*- coding: utf-8 -*-
import os
import subprocess
import time
from utils import *

logfiles=['/private/var/log/fwxserver.log',
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

conffiles=['/usr/local/etc/fwxserver.conf',
          '/usr/local/filewave/apache/conf/mdm_auth.conf',
          '/usr/local/filewave/apache/conf/httpd.conf',
          '/usr/local/filewave/apache/conf/httpd_custom.conf',
          '/usr/local/filewave/django/filewave/settings.py',
          '/usr/local/filewave/django/filewave/settings_custom.py',
          '/usr/local/filewave/postgresql/conf/user_postgresql.conf',
          '/fwxserver/DB/pg_data/postgresql.conf',
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
                 '/fwxserver/DB/ldap.sqlite'
		]

sqlitedbbakfiles = ['/fwxserver/DB/admin.sqlite.bak',
                 '/fwxserver/DB/server.sqlite.bak',
                 '/fwxserver/DB/ldap.sqlite.bak'
                ]

pglogs_dir = '/fwxserver/DB/pg_data/pg_log'
pgdump_command = '/usr/local/filewave/postgresql/bin/pg_dump'
copy_pgdata_command = 'ditto /fwxserver/DB/pg_data "%s"'

fwxserver = '/usr/local/sbin/fwxserver'

#local file storage
TEMPFILEPATH='/tmp/fwuploader/'
LICFILE='/usr/local/etc/fwxcodes'
DATAFILEPATH='/tmp'


def call_sqlite3(args):
    cmdline = '/usr/bin/sqlite3 %s' % args
    subprocess.call(cmdline, shell=True)

def gather_platform_data(progress_bar, infofilelist, directory):
    for sysinfofile in infofilelist:
        copy_temp_conffile(sysinfofile,directory)
    progress_bar("Gathering system information",50)

    #get network information
    subprocess.call('/bin/netstat -rn 2>/dev/null >%s' % os.path.join(directory,"routes.txt"),shell=True)
    subprocess.call('/sbin/ifconfig -v 2>/dev/null >%s' % os.path.join(directory,"ifconfig.txt"),shell=True)
    progress_bar("Gathering system information",75)

    subprocess.call('/sbin/ip a 2>/dev/null >%s' % os.path.join(directory,"ip-a-allhardwareports.txt"),shell=True)

    #get disk space, running processes snapshot etc.
    subprocess.call('/bin/ps waux 2>/dev/null >%s' % os.path.join(directory,"processes.txt"),shell=True)
    subprocess.call('/bin/df -h 2>/dev/null >%s' % os.path.join(directory,"diskspace.txt"),shell=True)

def get_os_info():
    osinfo = check_output(['cat','/etc/redhat-release'])
    osinfo = osinfo.replace('\n','')
    osinfo = osinfo.replace('(','')
    osinfo = osinfo.replace(')','')
    return osinfo

def is_postgresql_running():
    return 'fwxserver/DB/pg_data' in check_output(['ps','ax'])

def start_postgresql():
    subprocess.call(['su',
                     'postgres',
                     '-c',
                     'cd / ; /usr/local/filewave/postgresql/bin/pg_ctl start -w -t 10 -D /fwxserver/DB/pg_data -s >>/var/log/fw-mdm-server-postgres.log 2>&1'])
    time.sleep(3)

def get_free_disk_space():
    freespace = os.statvfs('/')
    return (freespace.f_bavail * freespace.f_frsize) / 1024

def copy_to_clipboard(text):
    raise OSError()

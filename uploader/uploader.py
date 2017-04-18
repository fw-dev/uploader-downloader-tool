#!/usr/bin/python
# -*- coding: utf-8 -*-
import os,sys,subprocess,time,shutil,threading
import json,codecs,tarfile,bz2
import pysftp
import pkg_resources
from distutils.version import StrictVersion
from utils import *

#amount of lines to gather of logfiles
LINESTOGATHER=10000

if is_windows:
    from platform_windows import *
elif is_mac:
    from platform_mac import *
elif is_linux:
    from platform_linux import *
else:
    print "Unsupported platform."
    sys.exit(1)


## datafilename = userid +"-"+ fwxversion +"-"+ osinfo +"-"+timestring+".tar.bz2"
# FILE CONTENTS AND STRUCTURE BELOW
#Things to gather up for submission
LOGFILESUBDIRECTORY = 'logs'
NUMBER_OF_PG_LOGS = 20  ## Amount of postgres logs to gather - there's one per day usually

DBFILESSUBDIRECTORY = 'dbs'
CONFFILESSUBDIRECTORY = 'config'
SYSTEMINFOSUBDIRECTORY = 'sysinfo'

#server information
SERVERNAME='ut.filewave.com'
CREATORUSER='creator'
CREATORPWD='CREATOR_PASSWORD_HERE'
CREATORDIRECTORY='createme'
USERPWD='USER_PASSWORD_HERE'
UPLOADPORT=32000

######### END OF SETTINGS ############

######### SFTP FUNCTIONALITY ##########
def create_sftpusername():
    #retreive the uuid we use for identification
    try :
        licfile = open(LICFILE,'r')
        licjson = json.loads(licfile.read())
        licid = licjson['uuid']
        licfile.close()
    except :
        ### TBD : Create 32bit eval id string containing servername ####
        licid = "0110010101110110011000010000eval"
        #print "no unique identification file found .. generating id for identification"
    return(licid)

def create_sftp_connection(userid, password):
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None # won't use known_hosts
    conninfo = {'host':SERVERNAME, 'username':userid, 'password':password, 'port':UPLOADPORT, 'cnopts': cnopts}
    return pysftp.Connection(**conninfo)

def create_sftpuser(userid):
    #creates an sftp user on the support site by placing a file with the desired username on it on the box
    #create an empty flagfile for upload
    try:
        if not os.path.exists(TEMPFILEPATH):
            os.mkdir(TEMPFILEPATH)
        markerfile = open(os.path.join(TEMPFILEPATH,userid), 'w')
        markerfile.write(userid)
        markerfile.close()
    except:
        print "Could not create temporary file. Aborting..."
        sys.exit(1)

    #connect to the sftp , and create an account by placing a markerfile ; disconnect from marker account
    try:
        with create_sftp_connection(CREATORUSER, CREATORPWD) as creatorsftp:
            with creatorsftp.cd(CREATORDIRECTORY):
                creatorsftp.put('%s/%s' % (TEMPFILEPATH,userid))
    except :
        print sys.exc_info()[0]
        print "Could not connect to %s on port %s - please verify this works and try again." % (SERVERNAME,UPLOADPORT)
        sys.exit(1)
    # temp file cleanup
    try:
        os.remove('%s/%s' % (TEMPFILEPATH,userid))
    except:
        print sys.exc_info()[0]
        print "Failed to remove temporary file. Continuing..."

def upload_data(userid,datafile):
    #connect using the user's account, upload a file, and disconnect
    try:
        with create_sftp_connection(userid, USERPWD) as userftp:
            userftp.put(datafile)
    except IOError as e:
        print "I/O error : %s while uploading - please try again" % e
        sys.exit(0)

    except :
        print sys.exc_info()[0]
        print "Could not connect to %s on port %s - please verify this works and try again" % (SERVERNAME,UPLOADPORT)
        sys.exit(1)

######### END OF SFTP FUNCTIONALITY ##########

######### INFORMATION GATHERING FUNCTIONALITY ##########

def get_lastlines(logfile,lines=LINESTOGATHER):
    #thanks to http://stackoverflow.com/a/13790289
    try:
        #logfile = codecs.open(logfile,'r','utf-8')
        logfile = open(logfile,'r')
        lines_found = []
        block_counter = -1
        # loop until we find X lines
        while len(lines_found) < lines:
            try:
                logfile.seek(block_counter * 4098, os.SEEK_END)
            except IOError:  # either file is too small, or too many lines requested
                logfile.seek(0)
                lines_found = logfile.readlines()
                break
            lines_found = logfile.readlines()
            # we found enough lines, get out
            if len(lines_found) > lines:
                break
            # decrement the block counter to get the
            # next X bytes
            block_counter -= 1
        return lines_found[-lines:]
    except:
        print "\nUnable to open logfile %s , skipping" % logfile
        return ''

def get_fwxserver_version():
    global fwxversion
    fwxversion = check_output([fwxserver,'-V'])
    fwxversion = fwxversion.replace('fwxserver ','')
    fwxversion = fwxversion.replace('\r','')
    fwxversion = fwxversion.replace('\n','')

def check_fwxserver_requires_sqlite():
    return StrictVersion(fwxversion) < StrictVersion('10.9')

def get_pg_log_files(directory=os.path.join(TEMPFILEPATH,LOGFILESUBDIRECTORY,'pg_log')):
    try:
        if not os.path.exists(directory):
            os.mkdir(directory)
        for logfile in pglogs[-NUMBER_OF_PG_LOGS:]:
            shutil.copy2(os.path.join(pglogs_dir,logfile),directory)
    except:
        print sys.exc_info()[0]
        print "Error copying pg_log files to %s - is there enough space?" % directory
        sys.exit(1)

def gather_migration_logs(migrationlogs,directory=os.path.join(TEMPFILEPATH,LOGFILESUBDIRECTORY)):
    try:
        if not os.path.exists(directory):
            os.mkdir(directory)
        for logfile in migrationlogs:
            if 'fwxserver-migration-' in logfile:
                shutil.copy2(os.path.join('/var/log',logfile),directory)
            if 'fw-mdm-server-migration-' in logfile:
                shutil.copy2(os.path.join('/var/log',logfile),directory)
    except:
        print sys.exc_info()[0]
        print "Error copying migration logfiles to %s - skipping ..." % directory

def write_temp_logfile(content,filename,directory=os.path.join(TEMPFILEPATH,LOGFILESUBDIRECTORY)):
    if not os.path.exists(directory):
        os.mkdir(directory)
    try:
        tempfile=os.path.join(directory,filename)
        templog=codecs.open(tempfile,'w','utf-8')
        for line in content:
            templog.write(line.decode('utf-8','ignore'))
        templog.close()
    except:
        print sys.exc_info()[0]
        print "Unable to write temporary logfile to %s - is there enough space?" % directory
        sys.exit(1)

def get_sqlitedump(dbpath,directory=os.path.join(TEMPFILEPATH,DBFILESSUBDIRECTORY)):
    if not os.path.exists(directory):
        os.mkdir(directory)
    try:
        args = '"%s" .dump >"%s"' % (dbpath,os.path.join(directory,os.path.split(dbpath)[1]+".dump"))
        call_sqlite3(args)
    except:
        print sys.exc_info()[0]
        print "Unable to dump sqlite database %s - is there enough space? is sqlite3 available?" % dbpath
        sys.exit(1)

def get_postgresqldump(directory=os.path.join(TEMPFILEPATH,DBFILESSUBDIRECTORY)):
    if not os.path.exists(directory):
        os.mkdir(directory)
    try:
        command = [pgdump_command,
                   '-U', 'django',
                   '--encoding=UTF8',
                   '-c',
                   '-f',
                   os.path.join(directory,"mdm-sql.dump"),
                   '-N', 'committed_*',
                   'mdm']
        subprocess.call(command)
    except:
        print sys.exc_info()[0]
        print "Unable to dump PostgreSQL database - is there enough space?"

    pgfailed = False
    try:
        if os.stat((os.path.join(directory,"mdm-sql.dump"))).st_size < 100:
            pgfailed = True
    except:
        pgfailed = True

    if pgfailed == True:
        print "PostgreSQL dump failure detected. Recovering raw data ..."
        try:
            subprocess.call(copy_pgdata_command % (os.path.join(directory,'pg_data')), shell=True)
        except:
            print sys.exc_info()[0]
            print "Unable to copy raw postgres data directory."

def gather_system_data(infofilelist, directory=os.path.join(TEMPFILEPATH,SYSTEMINFOSUBDIRECTORY)):
    if not os.path.exists(directory):
        os.mkdir(directory)

    progress_bar("Gathering system information")
    progress=0
    gather_platform_data(progress_bar, infofilelist, directory)
    progress_bar("Gathering system information",100)

def expand_wildcards_in_list(filelist):
    for entry in filelist:
        if "*" in entry:
            filelist.remove(entry)
            for subfile in os.listdir(os.path.split(entry)[0]):
                if os.path.isfile(os.path.join(os.path.split(entry)[0],subfile)):
                    filelist.append(os.path.join(os.path.split(entry)[0],subfile))
    return filelist
######### END OF INFORMATION GATHERING FUNCTIONALITY ##########


######### PROGRESS DISPLAY FUNCTIONALITY ##########
def progress_bar(statusmessage,progress=0):
    if progress>90: progress=100
    sys.stdout.write('\r{0: <30} [{1: <10}] {2}%'.format(statusmessage,'#'*(progress/10), progress))
    if progress==100: sys.stdout.write('\n')
    sys.stdout.flush()

class progress_indicator(threading.Thread):
    #thanks to http://thelivingpearl.com/2012/12/31/creating-progress-bars-with-python/
    def run(self):
            global stop
            global kill
            sys.stdout.write('%-30s  ' % statusmessage)
            sys.stdout.flush()
            i = 0
            while stop != True:
                    if (i%4) == 0:
                    	sys.stdout.write('\b/')
                    elif (i%4) == 1:
                    	sys.stdout.write('\b-')
                    elif (i%4) == 2:
                    	sys.stdout.write('\b\\')
                    elif (i%4) == 3:
                    	sys.stdout.write('\b|')
                    sys.stdout.flush()
                    time.sleep(0.2)
                    i+=1
            if kill == True:
            	print '\b\b\b\b Failed!',
            else:
            	print '\b\b Success'

def unknown_length_status(function,parameters,statusstring):
    #wrapper for starting progress display in separate thread
    global kill
    global stop
    kill = False
    stop = False
    global statusmessage
    statusmessage = statusstring
    p = progress_indicator()
    p.start()
    try:
        function(*parameters)
        stop = True
        p.join()
    except KeyboardInterrupt or EOFError:
         kill = True
         stop = True
         p.join()

######### END OF PROGRESS DISPLAY FUNCTIONALITY ##########

######### ARCHIVE MANAGEMENT AND CLEANUP FUNCTIONALITY ##########

def pack_data(TEMPFILEPATH,DATAFILEPATH,datafilename):
    #pack it all up and name it in a way that makes sense
    #DATAFILENAME=userid+".tar.bz2"
    try:
        datafile = tarfile.open(os.path.join(DATAFILEPATH,datafilename),'w:bz2')
        datafile.add(TEMPFILEPATH, arcname='.', recursive=True)
        datafile.close()
    except:
        print sys.exc_info()[0]
        print "Unable to write compressed file for upload. Is there enough space? Aborting."
        sys.exit(1)

def cleanup(TEMPFILEPATH,datafile):
    try:
        shutil.rmtree(TEMPFILEPATH)
        os.remove(datafile)
    except:
        print sys.exc_info()[0]
        print "Failed to clean up temporary file. Continuing..."

######### END OF ARCHIVE MANAGEMENT AND CLEANUP FUNCTIONALITY ##########

######### INFORMATION GATHERING MASTER FUNCTIONS  ##########
def gather_filewave_data(logfiles,noroot):
    #gather our debug data to upload

    progress_bar("Gathering filewave logfiles")
    progress=0
    for logfile in logfiles:
        write_temp_logfile(get_lastlines(logfile),os.path.split(logfile)[1])
        progress=progress+100/len(logfiles)
        progress_bar("Gathering filewave logfiles",progress)
    if noroot != 1:
        progress_bar("Gathering postgres logfiles",0)
        get_pg_log_files()
        progress_bar("Gathering postgres logfiles",100)

    if requires_sqlite:
        progress_bar("Gathering sqlite Databases")
        progress=0
        for sqlitedb in sqlitedbfiles:
            get_sqlitedump(sqlitedb)
            progress=progress+100/len(sqlitedbfiles)
            progress_bar("Gathering sqlite Databases",progress)

    else:
	progress_bar("Gathering sqlite backups")
        progress=0
        for sqlitedb in sqlitedbbakfiles:
            get_sqlitedump(sqlitedb)
            progress=progress+100/len(sqlitedbbakfiles)
            progress_bar("Gathering sqlite backups",progress)

    progress_bar("Gathering postgres Database",0)
    get_postgresqldump()
    progress_bar("Gathering postgres Database",100)

    progress_bar("Gathering configuration files")
    progress=0
    for conffile in conffiles:
        copy_temp_conffile(conffile,os.path.join(TEMPFILEPATH,CONFFILESSUBDIRECTORY))
        progress=progress+100/len(conffiles)
        progress_bar("Gathering configuration files",progress)

######### MAIN FUNCTION ###########
print "FileWave Debug Information Uploader"

try:
    get_fwxserver_version()
except:
    print "FileWave Server is not installed."
    sys.exit(1)

requires_sqlite = check_fwxserver_requires_sqlite()

#check for root rights
try:
    pglogs = os.listdir(pglogs_dir)
    noroot = 0
    if not is_postgresql_running():
        print "Attempting to start Postgres DB ..."
        start_postgresql()
except OSError:
    print "!! No root rights. Cannot access all information - please run as sudo to collect everything !!"
    noroot = 1
    if not is_postgresql_running():
        print "Cannot start postgres service because of no root rights - aborting. Please run again as root."
        sys.exit(1)

#if there's less than 500 MB free on / , we'll give up at this point.
if get_free_disk_space() < 500000:
    print ("Less than 500 MB space available on / filesystem. Free space and try again - aborting !")
    sys.exit(1)

#SFTP Functions : Create a user on the sftp
userid = create_sftpusername()
create_sftpuser(userid)

#Gather FileWave specific data - dbs , logfiles, config files etc.
gather_filewave_data(logfiles,noroot)

#special for linux : gather migration logfiles
if is_linux:
    migrationlogs = os.listdir('/var/log')
    gather_migration_logs(migrationlogs)

#Gather system specific configuration files
sysinfofiles = expand_wildcards_in_list(sysinfofiles)
gather_system_data(sysinfofiles)

#Pack up all gathered data into a .tar.bz2
osinfo = get_os_info()
timestring = time.strftime("%Y-%m-%d--%H-%M", time.gmtime())
datafilename = userid +"-"+ fwxversion +"-"+ osinfo +"-"+timestring+".tar.bz2"
unknown_length_status(pack_data,(TEMPFILEPATH,DATAFILEPATH,datafilename),"Compressing Data... ")
#upload the data
unknown_length_status(upload_data,(userid,os.path.join(DATAFILEPATH,datafilename)),"Uploading Data... ")
#tell the user we're done and clean up
print "Successfully uploaded \n\"%s\"\n" % datafilename

try:
    copy_to_clipboard(datafilename)
    print "#########################################################"
    print "The upload identifier has been copied to your clipboard."
    print "Please paste it into your support ticket."
    print "#########################################################"
except:
    print "Please attach the above line to your support ticket."

cleanup(TEMPFILEPATH,os.path.join(DATAFILEPATH,datafilename))

if is_windows:
    try:
        yep=input("Press the ENTER key to close this window")
    except:
        pass

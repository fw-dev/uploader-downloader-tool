# -*- coding: utf-8 -*-
import os
import shutil
import subprocess
import sys

is_mac = 'darwin' in sys.platform
is_windows = not is_mac and 'win' in sys.platform
is_linux = 'linux' in sys.platform

def check_output(args):
    if sys.version_info >= (2,7):
        return subprocess.check_output(args)
    else:
        return subprocess.Popen(args,stdout=subprocess.PIPE).communicate()[0]

def mkdir_p(path):
    #thanks to http://stackoverflow.com/a/600612
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise

def concatenate_paths(a,b):
    if is_windows:
        return os.path.join(a,b.replace('C:\\','').replace('c:\\',''))
    else:
        return a+b

def copy_temp_conffile(sourcefile,directory):
    #conffiles need to be copied with their path for easier restoration for repro
    originaldirectory = os.path.split(sourcefile)[0]
    filename = os.path.split(sourcefile)[1]
    destinationdirectory = concatenate_paths(directory, originaldirectory)

    if not os.path.exists(destinationdirectory):
        mkdir_p(destinationdirectory)
    try:
        shutil.copy(sourcefile,destinationdirectory)
    except IOError:  ## in case we can't be run as root, we can't access some of these files. we still have to continue ...
        pass
    except:
        print sys.exc_info()[1]
        print "Unable to write temporary config file to %s - is there enough space?" % directory
        sys.exit(1)

# -*- coding: utf-8 -*-
import __builtin__
import os
import subprocess
import sys
import threading
import time

is_mac = 'darwin' in sys.platform
is_windows = not is_mac and 'win' in sys.platform
is_linux = 'linux' in sys.platform

__builtin__.VERBOSE = False

_FNULL = open(os.devnull, 'wb')


def progress_bar(statusmessage, progress = 0):
    if progress > 90:
        progress = 100
    sys.stdout.write('\r{0: <40} [{1: <10}] {2}%'.format(statusmessage, '#'*(progress/10), progress))
    if progress == 100:
        sys.stdout.write('\n')
    sys.stdout.flush()


class progress_indicator(threading.Thread):
    # thanks to http://thelivingpearl.com/2012/12/31/creating-progress-bars-with-python/
    def run(self):
        global stop
        global kill
        sys.stdout.write('%-40s  ' % statusmessage)
        sys.stdout.flush()
        i = 0
        while not stop:
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
                i += 1
        if kill:
            print '\b\b\b\b Failed!',
        else:
            print '\b\b Success'


def unknown_length_status(function, parameters, statusstring):
    if __builtin__.VERBOSE:
        print statusstring
        return function(*parameters)
    else:
        # wrapper for starting progress display in separate thread
        global kill
        global stop
        kill = False     
        stop = False
        global statusmessage
        statusmessage = statusstring
        p = progress_indicator()
        p.start()
        try:
            result = function(*parameters)
            stop = True
            p.join()
            return result
        except:
            kill = True
            stop = True
            p.join()
            raise

        return None


def get_stdout():
    if __builtin__.VERBOSE:
        return None
    else:
        return _FNULL


def get_stderr():
    if __builtin__.VERBOSE:
        return None
    else:
        return subprocess.STDOUT


def subprocess_call(args, shell=False):
    env = os.environ.copy()
    try:
        del env['PYTHONHOME']
    except:
        pass

    try:
        del env['PYTHONPATH']
    except:
        pass

    error = subprocess.call(args, shell=shell, stdout=get_stdout(), stderr=get_stderr(), env=env)
    if error == 1:
        raise OSError(error)


def subprocess_call_ignoreerror(args, shell=False):
    try:
        subprocess_call(args, shell=shell)
    except OSError:
        pass

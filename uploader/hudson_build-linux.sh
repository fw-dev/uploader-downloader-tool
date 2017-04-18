#!/bin/sh

/opt/python2.7.13/bin/virtualenv ./venv
. ./venv/bin/activate
CFLAGS="-I/usr/include/libffi/include -I/usr/include/openssl101e/" pip install pysftp pyinstaller requests
./build.sh
deactivate

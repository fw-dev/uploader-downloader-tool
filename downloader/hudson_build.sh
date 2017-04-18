#!/bin/sh

/usr/local/bin/pip install virtualenv
/usr/local/bin/virtualenv ./venv
. ./venv/bin/activate
pip install pyinstaller
pip install pysftp
./build.sh
deactivate

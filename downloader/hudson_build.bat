C:\python27\Scripts\virtualenv.exe .\venv
call .\venv\Scripts\activate.bat
pip install pysftp pyinstaller requests
pyinstaller.exe downloader-windows.spec
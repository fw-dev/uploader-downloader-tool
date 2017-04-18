# -*- mode: python -*-
import inspect, os

current_dir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

a = Analysis(['uploader.py'],
             pathex=[os.path.join(os.environ['USERPROFILE'],'Desktop')],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None)
a.binaries += [('sqlite3.exe', os.path.join(current_dir,'sqlite3.exe'),'BINARY')]
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='uploader.exe',
          debug=False,
          strip=None,
          upx=True,
          console=True )

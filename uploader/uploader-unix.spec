# -*- mode: python -*-
a = Analysis(['uploader.py'],
             pathex=['/uploader'],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='uploader',
          debug=False,
          strip=None,
          upx=True,
          console=True )

# -*- mode: python -*-
a = Analysis(['downloader.py'],
             pathex=['/downloader'],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='downloader',
          debug=False,
          strip=None,
          upx=True,
          console=True )

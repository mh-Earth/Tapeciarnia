# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(
    ['main.py'],
    pathex=['.'], # Start search in the current directory
    binaries=[
        # mpv binaries/DLLs
        ('bin/mpv/mpv.exe', 'bin/mpv'),
        ('bin/mpv/libaacs.dll', 'bin/mpv'),
        ('bin/mpv/libbdplus.dll', 'bin/mpv'),
        ('bin/mpv/mpv.com', 'bin/mpv'),
        
        # weebp binaries/DLLs
        ('bin/weebp/wp.exe', 'bin/weebp'),
        ('bin/weebp/wp-headless.exe', 'bin/weebp'),
        ('bin/weebp/weebp.dll', 'bin/weebp'),
        ('bin/weebp/weebp.lib', 'bin/weebp'),

        # tools executables
        ('bin/tools/autoPause.exe', 'bin/tools'),
        ('bin/tools/refresh.exe', 'bin/tools'),
    ],
    datas=[
        # Application Data
        ('translations', 'translations'),
        
        # UI/Style/Icon Resources
        ('ui/style/style.qss', 'ui/style'),
        ('ui/icons', 'ui/icons'), # Includes all .png and .svg files

        # Binary Support Files
        ('bin/media/icon.ico', 'bin/media'),
        ('bin/mpv/mpv.conf', 'bin/mpv'),
        ('bin/mpv/README.txt', 'bin/mpv'),
        ('bin/weebp/README.txt', 'bin/weebp'),
        ('bin/tools/autoPause.au3', 'bin/tools'),
        ('bin/tools/refresh.au3', 'bin/tools'),
        
    ],
    hiddenimports=['utils'],
    hookspath=['hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Tapeciarnia',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='bin/media/icon.ico', # Set the application icon
)
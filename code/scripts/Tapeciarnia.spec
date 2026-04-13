# -*- mode: python ; coding: utf-8 -*-
# Description: PyInstaller spec file for building the Tapeciarnia application. This file defines how the application should be packaged, including which scripts to include, which data files and binaries to bundle, and how to configure the executable. It also includes a custom message handler to route Qt messages to the logging system for better debugging and error tracking. The spec file is designed to work in both development and packaged environments, with dynamic imports based on the execution context.

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
        #('bin/tools/refresh.exe', 'bin/tools'),

        ('bin/tools/autoPause.exe', 'bin/tools'),
        ('bin/tools/ffmpeg.exe', 'bin/tools'),
        ('bin/LICENSES/ffmpeg.txt', 'bin/LICENSES'),
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
        #('bin/mpv/README.txt', 'bin/mpv'),
        #('bin/weebp/README.txt', 'bin/weebp'),
        #('bin/tools/autoPause.au3', 'bin/tools'),
        #('bin/tools/refresh.au3', 'bin/tools'),
        
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
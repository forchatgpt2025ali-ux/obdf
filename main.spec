# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Critical for PySide6, Matplotlib, and Pandas/SciPy to find their underlying C-libraries
hidden_imports = [
    'scipy.special.cython_special',
    'scipy.optimize.minpack2',
    'matplotlib.backends.backend_qtagg',
    'openpyxl',
    'xlsxwriter',
    'pandas'
]

# Collect any dynamic submodules for SciPy
hidden_imports += collect_submodules('scipy')

# Bundle sample CSVs and UI assets
datas = [
    ('assets/app_icon.ico', 'assets'),
    ('data/sample_validation.csv', 'data')
]

a = Analysis(
    ['main.py'],  # Your app entry point
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'PyQt5'], # Avoid bundling conflicting Qt versions
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='GasKickSimulator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,           # UPX compression to reduce size
    console=False,      # Hides the Windows Command Prompt
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/app_icon.ico'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='GasKickSimulator',
)
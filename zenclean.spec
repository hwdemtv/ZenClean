# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

block_cipher = None
_ROOT = Path(os.getcwd()).absolute()

a = Analysis(
    ['src/main.py'],
    pathex=[str(_ROOT), str(_ROOT / 'src')],
    binaries=[],
    datas=[
        ('src/config/file_kb.json', 'config'),
        ('assets/*', 'assets'),
        # .env 不再打包，改为运行时从 exe 同级目录或系统环境变量读取
    ],
    hiddenimports=[
        'flet',
        'multiprocessing',
        'structlog',
        'pydantic',
        'send2trash',
        'machineid',
        'packaging',
        'utils.config_crypto',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['src/hooks/rthook.py'],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

splash = Splash(
    'assets/icon.png',
    binaries=a.binaries,
    datas=a.datas,
    text_pos=None,
    text_size=12,
    minify_script=True,
    always_on_top=True
)

exe_dir = EXE(
    pyz,
    a.scripts,
    splash,
    splash.binaries,
    [],
    exclude_binaries=True,
    name='ZenClean',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False, # 防止杀毒软件把 UPX 报毒
    console=False, # 生产环境禁用控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',
    uac_admin=False, # 先不在这里提权，代码里有兜底
)
coll = COLLECT(
    exe_dir,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='ZenClean',
)

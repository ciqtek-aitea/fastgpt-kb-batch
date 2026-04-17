# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — fastgpt-kb-batch 打包配置"""

import sys
from pathlib import Path

block_cipher = None

ROOT = Path(SPECPATH)
STATIC_DIR = ROOT / "backend" / "app" / "static"

# 如果 static 目录不存在，报错提示先构建前端
if not STATIC_DIR.exists():
    print("ERROR: backend/static/ 不存在，请先运行: python build.py")
    sys.exit(1)

a = Analysis(
    [str(ROOT / "backend" / "app" / "main.py")],
    pathex=[str(ROOT / "backend")],
    binaries=[],
    datas=[
        (str(STATIC_DIR), "app/static"),
    ],
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "httpx",
        "fastapi",
        "starlette",
        "starlette.routing",
        "starlette.middleware.cors",
        "starlette.staticfiles",
        "pydantic",
        "multipart",
        "websockets",
    ],
    hookspath=[],
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
    a.zipfiles,
    a.datas,
    [],
    name="fastgpt-kb-batch",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

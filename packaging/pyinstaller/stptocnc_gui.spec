# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for STPtoCNC operator GUI (Windows desktop build).

Build:
  python packaging/tools/build_exe.py
"""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENTRY = PROJECT_ROOT / "src" / "stptocnc" / "gui_entry.py"

a = Analysis(
    [str(ENTRY)],
    pathex=[str(PROJECT_ROOT), str(PROJECT_ROOT / "src")],
    binaries=[],
    datas=[],
    hiddenimports=["openpyxl", "openpyxl.workbook", "tkinter"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="STPtoCNC",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="STPtoCNC",
)

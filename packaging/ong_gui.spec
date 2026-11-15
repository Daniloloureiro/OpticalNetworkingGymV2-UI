# -*- mode: python ; coding: utf-8 -*-
"""Especificação PyInstaller multiplataforma (Windows e Linux) para o Optical Networking Gym v2."""

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

SPEC_DIR = Path(SPECPATH).resolve()
PROJECT_ROOT = SPEC_DIR.parent
SRC_DIR = PROJECT_ROOT / "OpticalNetworkingGymV2" / "src"
PKG_DIR = SRC_DIR / "optical_networking_gym_v2"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Arquivos de topologias ópticas (.xml e .txt)
datas = [
    (str(PKG_DIR / "topologies"), "optical_networking_gym_v2/topologies"),
]

hiddenimports = sorted(
    set(
        collect_submodules("optical_networking_gym_v2")
        + [
            "optical_networking_gym_v2.optical.kernels.allocation_kernel",
            "optical_networking_gym_v2.optical.kernels.qot_kernel",
            "optical_networking_gym_v2.simulation._request_analysis_kernels",
        ]
    )
)

# Exclui pacotes pesados não utilizados pela GUI para reduzir drasticamente o tamanho do executável
excludes = [
    "matplotlib",
    "pandas",
    "scipy",
    "pytest",
    "Cython",
    "tkinter",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtQuick",
    "PySide6.QtQuickWidgets",
    "PySide6.QtQml",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DRender",
    "PySide6.QtMultimedia",
]

a = Analysis(
    [str(SPEC_DIR / "entry_gui.py")],
    pathex=[str(SRC_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="OpticalNetworkingGymV2",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="OpticalNetworkingGymV2",
)

# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("dr_config.json", "."),
        ("ui/styles/light.qss", "ui/styles"),
        ("ui/styles/dark.qss", "ui/styles"),
    ],
    hiddenimports=collect_submodules("yfinance") + ["cachetools"],
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
    name="DRPriceEvaluator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon="dr_thai_price_evaluator_logo.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name="DRPriceEvaluator",
)

# -*- mode: python ; coding: utf-8 -*-
# Spec do PyInstaller — gera um único .exe Windows a partir de ui/app_desktop.py.
#
# Rodar (em Windows, ou via .github/workflows/build-exe.yml):
#   pyinstaller sapata7.spec
#
# Saída: dist/Sapata7.exe

a = Analysis(
    ["ui/app_desktop.py"],
    pathex=["."],
    binaries=[],
    datas=[],
    hiddenimports=[],
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
    a.binaries,
    a.datas,
    [],
    name="Sapata7",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,       # janela desktop, sem console atrás
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

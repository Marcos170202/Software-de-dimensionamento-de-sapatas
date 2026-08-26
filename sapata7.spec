# -*- mode: python ; coding: utf-8 -*-
# Spec do PyInstaller — gera dois .exe Windows, um por interface:
#   Sapata7.exe          <- ui/app_desktop.py   (escopo mínimo, 100% auditado)
#   Sapata7Completo.exe  <- ui/app_completo.py  (escopo amplo, ver ruleset.yaml)
#
# Rodar (em Windows, ou via .github/workflows/build-exe.yml):
#   pyinstaller sapata7.spec
#
# Saída: dist/Sapata7.exe e dist/Sapata7Completo.exe

a_minimo = Analysis(
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
pyz_minimo = PYZ(a_minimo.pure)

exe_minimo = EXE(
    pyz_minimo,
    a_minimo.scripts,
    a_minimo.binaries,
    a_minimo.datas,
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

a_completo = Analysis(
    ["ui/app_completo.py"],
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
pyz_completo = PYZ(a_completo.pure)

exe_completo = EXE(
    pyz_completo,
    a_completo.scripts,
    a_completo.binaries,
    a_completo.datas,
    [],
    name="Sapata7Completo",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

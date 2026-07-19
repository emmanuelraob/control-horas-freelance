# -*- mode: python ; coding: utf-8 -*-

# Empaquetado en modo "onedir" (una carpeta con el .exe + dependencias).
# IMPORTANTE: el dashboard usa Qt WebEngine, que NO funciona de forma fiable en
# modo "onefile" en Windows (el subproceso QtWebEngineProcess no encuentra sus
# recursos al extraerse a un temporal y el dashboard queda en blanco). onedir lo
# evita. Además UPX se desactiva porque puede corromper las DLLs de Qt6/WebEngine.

a = Analysis(
    ['control_horas\\main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('control_horas/dashboard/index.html', 'control_horas/dashboard'),
        ('control_horas/dashboard/style.css', 'control_horas/dashboard'),
        ('control_horas/dashboard/app.js', 'control_horas/dashboard'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ControlHorasFreelance',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='ControlHorasFreelance',
)

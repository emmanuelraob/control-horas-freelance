"""Registra la app para iniciar sola con el login de Windows, creando un
acceso directo en la carpeta de inicio del usuario. No requiere permisos de
administrador (a diferencia de un Windows Service, que arrancaría antes del
login pero es mucho más complejo de instalar)."""
from __future__ import annotations

import sys
from pathlib import Path

NOMBRE_ACCESO_DIRECTO = "ControlHorasFreelance.lnk"


def _shell():
    import win32com.client  # solo disponible en Windows (pywin32)

    return win32com.client.Dispatch("WScript.Shell")


def _carpeta_inicio() -> Path:
    return Path(_shell().SpecialFolders("Startup"))


def _ruta_acceso_directo() -> Path:
    return _carpeta_inicio() / NOMBRE_ACCESO_DIRECTO


def esta_registrado() -> bool:
    if sys.platform != "win32":
        return False
    return _ruta_acceso_directo().exists()


def registrar(
    ruta_ejecutable: str | Path, argumentos: str = "", carpeta_trabajo: str | Path | None = None
) -> Path:
    """Crea (o actualiza) el acceso directo en la carpeta de inicio de Windows."""
    destino = _ruta_acceso_directo()
    acceso_directo = _shell().CreateShortCut(str(destino))
    acceso_directo.TargetPath = str(ruta_ejecutable)
    acceso_directo.Arguments = argumentos
    acceso_directo.WorkingDirectory = str(carpeta_trabajo or Path(ruta_ejecutable).parent)
    acceso_directo.IconLocation = str(ruta_ejecutable)
    acceso_directo.Save()
    return destino


def quitar() -> None:
    ruta = _ruta_acceso_directo()
    if ruta.exists():
        ruta.unlink()


def registrar_si_hace_falta() -> None:
    """Registra el proceso actual (funciona tanto corriendo desde código
    fuente con `python main.py` como empaquetado con PyInstaller)."""
    if sys.platform != "win32" or esta_registrado():
        return

    ejecutable = Path(sys.executable)
    if ejecutable.name.lower() in ("python.exe", "pythonw.exe"):
        script = Path(sys.argv[0]).resolve()
        registrar(ejecutable, argumentos=f'"{script}"', carpeta_trabajo=script.parent)
    else:
        registrar(ejecutable)

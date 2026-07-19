"""Detección de inactividad de mouse/teclado usando la API nativa de Windows
`GetLastInputInfo` (user32.dll), sin interceptar qué tecla se presiona ni el
contenido de pantalla — solo el instante del último input.

Solo funciona en Windows. `segundos_inactivo()` es la única función que toca
`ctypes.windll`, así el resto del módulo se puede importar (y el resto de la
app testear) en cualquier plataforma.
"""
from __future__ import annotations

import ctypes
import sys
from datetime import datetime, timedelta

from PySide6.QtCore import QObject, QTimer, Signal


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def segundos_inactivo() -> float:
    """Segundos transcurridos desde el último movimiento de mouse o tecla."""
    if sys.platform != "win32":
        raise RuntimeError("segundos_inactivo() solo funciona en Windows")

    info = LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):  # type: ignore[attr-defined]
        raise OSError("GetLastInputInfo falló")
    millis_desde_boot = ctypes.windll.kernel32.GetTickCount()  # type: ignore[attr-defined]
    return max(0.0, (millis_desde_boot - info.dwTime) / 1000.0)


class IdleDetector(QObject):
    """Sondea `segundos_inactivo()` cada `intervalo_poll_ms` y emite señales
    cuando arranca/termina una pausa, o cuando hay actividad continua."""

    pausa_iniciada = Signal(datetime)
    pausa_terminada = Signal(datetime, datetime)  # inicio, fin
    actividad_detectada = Signal(datetime)

    def __init__(self, umbral_segundos: int, intervalo_poll_ms: int = 20_000, parent=None):
        super().__init__(parent)
        self.umbral_segundos = umbral_segundos
        self._en_pausa = False
        self._inicio_pausa: datetime | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(intervalo_poll_ms)
        self._timer.timeout.connect(self._poll)

    def start(self) -> None:
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def set_umbral_segundos(self, segundos: int) -> None:
        self.umbral_segundos = segundos

    def _poll(self) -> None:
        inactivo = segundos_inactivo()
        ahora = datetime.now()

        if inactivo >= self.umbral_segundos and not self._en_pausa:
            self._en_pausa = True
            self._inicio_pausa = ahora - timedelta(seconds=inactivo)
            self.pausa_iniciada.emit(self._inicio_pausa)
        elif inactivo < self.umbral_segundos and self._en_pausa:
            inicio = self._inicio_pausa
            fin = ahora - timedelta(seconds=inactivo)
            self._en_pausa = False
            self._inicio_pausa = None
            if inicio is not None:
                self.pausa_terminada.emit(inicio, fin)
            self.actividad_detectada.emit(ahora)
        elif not self._en_pausa:
            self.actividad_detectada.emit(ahora)

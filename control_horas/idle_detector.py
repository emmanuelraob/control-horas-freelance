"""Detección de inactividad de mouse/teclado.

En Windows (producción) usa la API nativa `GetLastInputInfo` (user32.dll):
solo lee el instante del último input, sin interceptar qué tecla se
presiona ni el contenido de pantalla. En macOS usa el equivalente de
Quartz (`CGEventSourceSecondsSinceLastEventType`) — el mismo tipo de API,
de solo lectura — únicamente para poder desarrollar y probar la app sin
tener una PC Windows a mano; la app en producción corre en Windows.
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
    if sys.platform == "win32":
        return _segundos_inactivo_windows()
    if sys.platform == "darwin":
        return _segundos_inactivo_macos()
    raise RuntimeError(f"Detección de inactividad no soportada en {sys.platform!r}")


def _segundos_inactivo_windows() -> float:
    info = LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):  # type: ignore[attr-defined]
        raise OSError("GetLastInputInfo falló")
    millis_desde_boot = ctypes.windll.kernel32.GetTickCount()  # type: ignore[attr-defined]
    return max(0.0, (millis_desde_boot - info.dwTime) / 1000.0)


def _segundos_inactivo_macos() -> float:
    from Quartz import (  # pyobjc-framework-Quartz; solo se instala/usa en macOS
        CGEventSourceSecondsSinceLastEventType,
        kCGAnyInputEventType,
        kCGEventSourceStateCombinedSessionState,
    )

    return max(
        0.0,
        CGEventSourceSecondsSinceLastEventType(kCGEventSourceStateCombinedSessionState, kCGAnyInputEventType),
    )


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

"""Garantiza que solo corra una copia de la app a la vez, y permite que un
segundo lanzamiento le pida a la instancia viva que muestre el dashboard (en
lugar de abrir una segunda copia que compita por la misma base de datos).

En Windows usamos un *named mutex* + un *evento* con prefijo ``Global\\`` de
pywin32. Son robustos entre sesiones de usuario y no dependen de named pipes.
Se probó ``QLocalServer`` primero y resultó poco fiable en Windows: un
``QLocalSocket`` de otro proceso no lograba conectarse al servidor (error
"Invalid name"), muy probablemente por el namespace de los pipes combinado con
el modelo stub+worker de los venv y con procesos lanzados en sesiones distintas.

En macOS/Linux (solo para probar) usamos ``QLocalServer``, que ahí sí anda bien
sobre sockets de dominio Unix.
"""
from __future__ import annotations

import sys
from typing import Callable

# Nombres globales (compartidos entre todas las sesiones del usuario en Windows).
NOMBRE_MUTEX = "Global\\ControlHorasFreelance-instancia-unica"
NOMBRE_EVENTO_MOSTRAR = "Global\\ControlHorasFreelance-mostrar-dashboard"
# Nombre plano para el socket local en macOS/Linux (no admite el prefijo Global\).
NOMBRE_SOCKET = "ControlHorasFreelance-instancia-unica"


class Candado:
    """Representa la 'propiedad' de la única instancia. Hay que mantener viva la
    referencia mientras la app corra: si se libera, otra copia podría arrancar."""

    def __init__(self) -> None:
        self._mutex = None  # PyHANDLE del mutex (Windows)
        self._servidor = None  # QLocalServer (macOS/Linux)
        self._timer = None  # QTimer que vigila el evento (Windows)
        self._evento = None  # PyHANDLE del evento (Windows)

    def vigilar_pedidos_de_mostrar(self, al_pedir_mostrar: Callable[[], None]) -> None:
        """Empieza a escuchar los avisos de "mostrá el dashboard" que manda un
        segundo lanzamiento, y llama a `al_pedir_mostrar` cuando llega uno."""
        if sys.platform == "win32":
            self._vigilar_windows(al_pedir_mostrar)
        elif self._servidor is not None:
            self._vigilar_socket(al_pedir_mostrar)

    def _vigilar_windows(self, al_pedir_mostrar: Callable[[], None]) -> None:
        import win32event
        from PySide6.QtCore import QTimer

        self._evento = win32event.CreateEvent(None, False, False, NOMBRE_EVENTO_MOSTRAR)

        def revisar() -> None:
            # WAIT_OBJECT_0 = el evento estaba señalado (otra copia lo activó).
            # Al ser auto-reset, leerlo lo vuelve a dejar en no-señalado.
            if win32event.WaitForSingleObject(self._evento, 0) == win32event.WAIT_OBJECT_0:
                al_pedir_mostrar()

        self._timer = QTimer()
        self._timer.setInterval(500)
        self._timer.timeout.connect(revisar)
        self._timer.start()

    def _vigilar_socket(self, al_pedir_mostrar: Callable[[], None]) -> None:
        def on_conexion() -> None:
            conexion = self._servidor.nextPendingConnection()
            if conexion is not None:
                conexion.disconnectFromServer()
            al_pedir_mostrar()

        self._servidor.newConnection.connect(on_conexion)


def intentar_adquirir() -> Candado | None:
    """Devuelve un `Candado` si esta copia es la primera; `None` si ya hay otra
    corriendo (en cuyo caso quien llama debería avisar y salir)."""
    if sys.platform == "win32":
        return _adquirir_windows()
    return _adquirir_socket()


def avisar_mostrar_dashboard() -> None:
    """Desde un segundo lanzamiento: le pide a la instancia viva que muestre el
    dashboard. Best-effort: si algo falla, simplemente no se abre."""
    if sys.platform == "win32":
        _avisar_windows()
    else:
        _avisar_socket()


# --------------------------------------------------------------- Windows

def _adquirir_windows() -> Candado | None:
    import win32api
    import win32event
    import winerror

    handle = win32event.CreateMutex(None, False, NOMBRE_MUTEX)
    if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
        # Ya existe el mutex: hay otra instancia. Soltamos este handle (el de la
        # instancia viva mantiene el mutex "ocupado").
        return None
    candado = Candado()
    candado._mutex = handle
    return candado


def _avisar_windows() -> None:
    try:
        import win32event

        evento = win32event.CreateEvent(None, False, False, NOMBRE_EVENTO_MOSTRAR)
        win32event.SetEvent(evento)
    except Exception:
        pass


# --------------------------------------------------------- macOS / Linux

def _adquirir_socket() -> Candado | None:
    from PySide6.QtNetwork import QLocalServer, QLocalSocket

    socket = QLocalSocket()
    socket.connectToServer(NOMBRE_SOCKET)
    if socket.waitForConnected(200):
        socket.abort()
        return None

    servidor = QLocalServer()
    QLocalServer.removeServer(NOMBRE_SOCKET)  # limpia un socket colgado de un cierre abrupto
    servidor.listen(NOMBRE_SOCKET)
    candado = Candado()
    candado._servidor = servidor
    return candado


def _avisar_socket() -> None:
    from PySide6.QtNetwork import QLocalSocket

    socket = QLocalSocket()
    socket.connectToServer(NOMBRE_SOCKET)
    if socket.waitForConnected(200):
        socket.waitForBytesWritten(100)
        socket.abort()

"""Ícono de la bandeja del sistema. El uso diario es 100% automático (ver
idle_detector.py + pause_popup.py); este menú es solo un respaldo manual
para corregir o marcar algo a mano cuando haga falta."""
from __future__ import annotations

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMenu, QStyle, QSystemTrayIcon
from PySide6.QtCore import Signal

from control_horas.classifier import ALMUERZO, BAÑO, MERIENDA, OTRA_COSA

OPCIONES_PAUSA_MANUAL = [
    ("Almuerzo", ALMUERZO),
    ("Merienda", MERIENDA),
    ("Baño", BAÑO),
    ("Otra cosa", OTRA_COSA),
]


class SystemTray(QSystemTrayIcon):
    entrada_manual_solicitada = Signal()
    salida_manual_solicitada = Signal()
    pausa_manual_solicitada = Signal(str)  # valor de OPCIONES_PAUSA_MANUAL
    dashboard_solicitado = Signal()
    configuracion_solicitada = Signal()
    salir_solicitado = Signal()

    def __init__(self, app: QApplication, parent=None):
        icono = app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        super().__init__(icono, parent)
        self.setToolTip("Control de Horas — sin marcar (automático)")

        menu = QMenu()

        accion_entrada = menu.addAction("Marcar entrada (manual)")
        accion_entrada.triggered.connect(self.entrada_manual_solicitada.emit)

        accion_salida = menu.addAction("Marcar salida (manual)")
        accion_salida.triggered.connect(self.salida_manual_solicitada.emit)

        menu.addSeparator()
        submenu_pausa = menu.addMenu("Marcar pausa actual como...")
        for etiqueta, valor in OPCIONES_PAUSA_MANUAL:
            accion = submenu_pausa.addAction(etiqueta)
            accion.triggered.connect(lambda _checked=False, v=valor: self.pausa_manual_solicitada.emit(v))

        menu.addSeparator()
        menu.addAction("Ver Dashboard").triggered.connect(self.dashboard_solicitado.emit)
        menu.addAction("Configuración").triggered.connect(self.configuracion_solicitada.emit)

        menu.addSeparator()
        menu.addAction("Salir").triggered.connect(self.salir_solicitado.emit)

        self.setContextMenu(menu)

    def actualizar_estado(self, texto: str) -> None:
        self.setToolTip(f"Control de Horas — {texto}")

    def notificar(self, titulo: str, mensaje: str) -> None:
        self.showMessage(titulo, mensaje, QSystemTrayIcon.MessageIcon.Information, 5000)

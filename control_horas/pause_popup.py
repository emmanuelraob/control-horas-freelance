"""Popup no bloqueante que aparece cuando arranca una pausa larga.

Responder es opcional, pero el popup **no se cierra solo por tiempo**: queda
abierto mientras dure la pausa. Se cierra en alguno de estos tres casos:
1. El usuario elige una opción (Almuerzo/Merienda/Baño/Otra cosa) -> queda
   clasificada como `origen=usuario`.
2. El usuario lo cierra a mano (la X de la ventana) sin elegir nada -> a partir
   de ahí, cuando la pausa termine, se clasifica sola por horario
   (`classifier.clasificar_pausa`).
3. Vuelve la actividad (el usuario retoma el mouse/teclado) -> lo cierra
   `main.py` llamando a `cerrar_por_fin_de_pausa()`, sin disparar la señal de
   "cerrado sin clasificar" (la pausa ya se está resolviendo por otro lado).
"""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from control_horas.classifier import ALMUERZO, BAÑO, MERIENDA, OTRA_COSA

OPCIONES = [
    ("Almuerzo", ALMUERZO),
    ("Merienda", MERIENDA),
    ("Baño", BAÑO),
    ("Otra cosa", OTRA_COSA),
]


class PausePopup(QWidget):
    clasificado = Signal(str)  # valor de OPCIONES
    cerrado_sin_clasificar = Signal()  # el usuario lo cerró sin elegir nada

    def __init__(self, inicio_pausa: datetime, parent=None):
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle("Control de Horas")
        self._inicio_pausa = inicio_pausa
        self._respondido = False
        self._cierre_silencioso = False

        self._label_contador = QLabel()
        self._label_contador.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Parece que te alejaste de la compu. ¿En qué estuviste?"))
        layout.addWidget(self._label_contador)

        botones = QHBoxLayout()
        for etiqueta, valor in OPCIONES:
            boton = QPushButton(etiqueta)
            boton.clicked.connect(lambda _checked=False, v=valor: self._responder(v))
            botones.addWidget(boton)
        layout.addLayout(botones)

        pie = QLabel("Si cerrás esta ventana sin elegir nada, la pausa se clasifica sola por horario.")
        pie.setWordWrap(True)
        layout.addWidget(pie)

        self._timer_contador = QTimer(self)
        self._timer_contador.setInterval(1000)
        self._timer_contador.timeout.connect(self._actualizar_contador)
        self._timer_contador.start()
        self._actualizar_contador()

    def _actualizar_contador(self) -> None:
        transcurrido = datetime.now() - self._inicio_pausa
        minutos, segundos = divmod(max(0, int(transcurrido.total_seconds())), 60)
        self._label_contador.setText(f"{minutos:02d}:{segundos:02d} sin actividad")

    def _responder(self, clasificacion: str) -> None:
        self._respondido = True
        self._timer_contador.stop()
        self.clasificado.emit(clasificacion)
        self.close()

    def cerrar_por_fin_de_pausa(self) -> None:
        """Cierre programático (volvió la actividad): no dispara `cerrado_sin_clasificar`."""
        self._cierre_silencioso = True
        self.close()

    def closeEvent(self, event) -> None:  # noqa: N802 (override de Qt)
        self._timer_contador.stop()
        if not self._respondido and not self._cierre_silencioso:
            self.cerrado_sin_clasificar.emit()
        super().closeEvent(event)

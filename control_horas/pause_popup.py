"""Popup no bloqueante que aparece cuando arranca una pausa larga.

Responder es opcional: el usuario puede clasificar la pausa con un click,
o simplemente ignorarlo y seguir trabajando. Si nadie responde antes de que
se cumpla `tiempo_espera_minutos`, se autocierra sin bloquear nada — la
pausa queda para que `classifier.clasificar_pausa` la infiera por horario.
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
    expirado = Signal()

    def __init__(self, inicio_pausa: datetime, tiempo_espera_minutos: int, parent=None):
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle("Control de Horas")
        self._inicio_pausa = inicio_pausa

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

        pie = QLabel("Podés ignorar esto y seguir trabajando; se clasifica solo por horario.")
        pie.setWordWrap(True)
        layout.addWidget(pie)

        self._timer_contador = QTimer(self)
        self._timer_contador.setInterval(1000)
        self._timer_contador.timeout.connect(self._actualizar_contador)
        self._timer_contador.start()
        self._actualizar_contador()

        self._timer_expiracion = QTimer(self)
        self._timer_expiracion.setSingleShot(True)
        self._timer_expiracion.setInterval(max(1, tiempo_espera_minutos) * 60 * 1000)
        self._timer_expiracion.timeout.connect(self._expirar)
        self._timer_expiracion.start()

    def _actualizar_contador(self) -> None:
        transcurrido = datetime.now() - self._inicio_pausa
        minutos, segundos = divmod(max(0, int(transcurrido.total_seconds())), 60)
        self._label_contador.setText(f"{minutos:02d}:{segundos:02d} sin actividad")

    def _responder(self, clasificacion: str) -> None:
        self._timer_contador.stop()
        self._timer_expiracion.stop()
        self.clasificado.emit(clasificacion)
        self.close()

    def _expirar(self) -> None:
        self._timer_contador.stop()
        self.expirado.emit()
        self.close()

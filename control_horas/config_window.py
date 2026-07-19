"""Ventana de configuración: horario esperado, ventana de almuerzo, ventanas
de merienda, tolerancias y umbral de inactividad. Todo lo que el clasificador
automático (classifier.py) usa para inferir pausas sin preguntar."""
from __future__ import annotations

from datetime import time

from PySide6.QtCore import QTime, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from control_horas.models import Config

DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def _time_to_qtime(t: time) -> QTime:
    return QTime(t.hour, t.minute)


def _qtime_to_time(qt: QTime) -> time:
    return time(qt.hour(), qt.minute())


class _FilaVentana(QWidget):
    eliminar_solicitado = Signal(QWidget)

    def __init__(self, inicio: time, fin: time, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.inicio_edit = QTimeEdit(_time_to_qtime(inicio))
        self.fin_edit = QTimeEdit(_time_to_qtime(fin))
        boton_quitar = QPushButton("Quitar")
        boton_quitar.clicked.connect(lambda: self.eliminar_solicitado.emit(self))

        layout.addWidget(self.inicio_edit)
        layout.addWidget(QLabel("a"))
        layout.addWidget(self.fin_edit)
        layout.addWidget(boton_quitar)

    def rango(self) -> tuple[time, time]:
        return _qtime_to_time(self.inicio_edit.time()), _qtime_to_time(self.fin_edit.time())


class ConfigWindow(QDialog):
    """Diálogo simple para editar y guardar la configuración de horario."""

    configuracion_guardada = Signal(Config)

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración — Control de Horas")
        self._filas_merienda: list[_FilaVentana] = []

        layout = QVBoxLayout(self)

        form_horario = QFormLayout()
        self.entrada_edit = QTimeEdit(_time_to_qtime(config.entrada_esperada))
        self.salida_edit = QTimeEdit(_time_to_qtime(config.salida_esperada))
        self.tolerancia_spin = QSpinBox()
        self.tolerancia_spin.setRange(0, 120)
        self.tolerancia_spin.setSuffix(" min")
        self.tolerancia_spin.setValue(config.tolerancia_minutos)
        form_horario.addRow("Hora de entrada esperada", self.entrada_edit)
        form_horario.addRow("Hora de salida esperada", self.salida_edit)
        form_horario.addRow("Tolerancia de puntualidad", self.tolerancia_spin)
        layout.addLayout(form_horario)

        grupo_almuerzo = QGroupBox("Almuerzo")
        form_almuerzo = QFormLayout(grupo_almuerzo)
        self.almuerzo_inicio_edit = QTimeEdit(_time_to_qtime(config.ventana_almuerzo_inicio))
        self.almuerzo_fin_edit = QTimeEdit(_time_to_qtime(config.ventana_almuerzo_fin))
        self.almuerzo_duracion_spin = QSpinBox()
        self.almuerzo_duracion_spin.setRange(0, 240)
        self.almuerzo_duracion_spin.setSuffix(" min")
        self.almuerzo_duracion_spin.setValue(config.duracion_esperada_almuerzo_min)
        form_almuerzo.addRow("Ventana permitida — desde", self.almuerzo_inicio_edit)
        form_almuerzo.addRow("Ventana permitida — hasta", self.almuerzo_fin_edit)
        form_almuerzo.addRow("Duración esperada", self.almuerzo_duracion_spin)
        layout.addWidget(grupo_almuerzo)

        grupo_merienda = QGroupBox("Merienda")
        self._layout_merienda = QVBoxLayout(grupo_merienda)
        for inicio, fin in config.ventanas_merienda or [(time(9, 30), time(10, 0))]:
            self._agregar_fila_merienda(inicio, fin)
        boton_agregar_merienda = QPushButton("+ Agregar otra ventana de merienda")
        boton_agregar_merienda.clicked.connect(lambda: self._agregar_fila_merienda(time(16, 0), time(16, 15)))
        self._layout_merienda.addWidget(boton_agregar_merienda)

        form_merienda_duracion = QFormLayout()
        self.merienda_duracion_spin = QSpinBox()
        self.merienda_duracion_spin.setRange(0, 120)
        self.merienda_duracion_spin.setSuffix(" min")
        self.merienda_duracion_spin.setValue(config.duracion_esperada_merienda_min)
        form_merienda_duracion.addRow("Duración esperada", self.merienda_duracion_spin)
        self._layout_merienda.addLayout(form_merienda_duracion)
        layout.addWidget(grupo_merienda)

        grupo_dias = QGroupBox("Días laborales")
        layout_dias = QHBoxLayout(grupo_dias)
        self.checks_dias: list[QCheckBox] = []
        for i, nombre in enumerate(DIAS_SEMANA):
            check = QCheckBox(nombre)
            check.setChecked(i in config.dias_laborales)
            layout_dias.addWidget(check)
            self.checks_dias.append(check)
        layout.addWidget(grupo_dias)

        grupo_deteccion = QGroupBox("Detección de inactividad")
        form_deteccion = QFormLayout(grupo_deteccion)
        self.umbral_idle_spin = QSpinBox()
        self.umbral_idle_spin.setRange(1, 60)
        self.umbral_idle_spin.setSuffix(" min")
        self.umbral_idle_spin.setValue(config.umbral_idle_minutos)
        self.tiempo_espera_popup_spin = QSpinBox()
        self.tiempo_espera_popup_spin.setRange(1, 30)
        self.tiempo_espera_popup_spin.setSuffix(" min")
        self.tiempo_espera_popup_spin.setValue(config.tiempo_espera_popup_minutos)
        self.pausa_corta_spin = QSpinBox()
        self.pausa_corta_spin.setRange(1, 60)
        self.pausa_corta_spin.setSuffix(" min")
        self.pausa_corta_spin.setValue(config.duracion_maxima_pausa_corta_min)
        form_deteccion.addRow("Inactividad para considerar pausa", self.umbral_idle_spin)
        form_deteccion.addRow("El popup se autocierra a los", self.tiempo_espera_popup_spin)
        form_deteccion.addRow("Máximo de una pausa corta (ej. baño)", self.pausa_corta_spin)
        layout.addWidget(grupo_deteccion)

        botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        botones.accepted.connect(self._guardar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    def _agregar_fila_merienda(self, inicio: time, fin: time) -> None:
        fila = _FilaVentana(inicio, fin)
        fila.eliminar_solicitado.connect(self._quitar_fila_merienda)
        self._filas_merienda.append(fila)
        self._layout_merienda.insertWidget(len(self._filas_merienda) - 1, fila)

    def _quitar_fila_merienda(self, fila: QWidget) -> None:
        if len(self._filas_merienda) <= 1:
            return  # siempre debe quedar al menos una ventana
        self._filas_merienda.remove(fila)
        fila.setParent(None)
        fila.deleteLater()

    def _guardar(self) -> None:
        nueva_config = Config(
            entrada_esperada=_qtime_to_time(self.entrada_edit.time()),
            salida_esperada=_qtime_to_time(self.salida_edit.time()),
            tolerancia_minutos=self.tolerancia_spin.value(),
            ventana_almuerzo_inicio=_qtime_to_time(self.almuerzo_inicio_edit.time()),
            ventana_almuerzo_fin=_qtime_to_time(self.almuerzo_fin_edit.time()),
            duracion_esperada_almuerzo_min=self.almuerzo_duracion_spin.value(),
            ventanas_merienda=[fila.rango() for fila in self._filas_merienda],
            duracion_esperada_merienda_min=self.merienda_duracion_spin.value(),
            dias_laborales=[i for i, check in enumerate(self.checks_dias) if check.isChecked()],
            umbral_idle_minutos=self.umbral_idle_spin.value(),
            tiempo_espera_popup_minutos=self.tiempo_espera_popup_spin.value(),
            duracion_maxima_pausa_corta_min=self.pausa_corta_spin.value(),
        )
        self.configuracion_guardada.emit(nueva_config)
        self.accept()

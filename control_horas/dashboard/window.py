"""Host QWebEngineView del dashboard. Lee resúmenes de SQLite y los inyecta
como JSON al HTML/JS local (sin servidor, sin depender de internet)."""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QVBoxLayout, QWidget

from control_horas import db
from control_horas.scoring import calcular_score_semana

RUTA_HTML = Path(__file__).parent / "index.html"
DIAS_HISTORIAL = 60


class DashboardWindow(QWidget):
    def __init__(self, conn, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dashboard — Control de Horas")
        self.resize(1150, 780)
        self._conn = conn

        self._view = QWebEngineView(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._view)

        self._view.loadFinished.connect(self._on_load_finished)
        self._view.load(QUrl.fromLocalFile(str(RUTA_HTML)))

    def _on_load_finished(self, ok: bool) -> None:
        if ok:
            self.actualizar()

    def showEvent(self, event) -> None:  # noqa: N802 (override de Qt)
        super().showEvent(event)
        self.actualizar()

    def actualizar(self) -> None:
        datos = self._recolectar_datos()
        script = f"window.renderDashboard({json.dumps(datos)});"
        self._view.page().runJavaScript(script)

    def _recolectar_datos(self) -> dict:
        hoy = date.today()
        desde = hoy - timedelta(days=DIAS_HISTORIAL - 1)
        resumenes = db.resumenes_rango(self._conn, desde, hoy)

        dias = [
            {
                "fecha": r.fecha,
                "entrada": r.entrada.strftime("%H:%M") if r.entrada else None,
                "salida": r.salida.strftime("%H:%M") if r.salida else None,
                "horas_trabajadas": round(r.segundos_trabajados / 3600, 2),
                "horas_idle": round(r.segundos_idle_sin_clasificar / 3600, 2),
                "duracion_almuerzo_min": round(r.duracion_almuerzo_seg / 60),
                "duracion_merienda_min": round(r.duracion_merienda_seg / 60),
                "score": r.score,
                "flags": r.flags,
            }
            for r in resumenes
        ]

        pausas_hoy = db.pausas_del_dia(self._conn, hoy)
        pausas_serializadas = [
            {
                "inicio": p.inicio.isoformat(),
                "fin": p.fin.isoformat() if p.fin else None,
                "clasificacion": p.clasificacion,
                "origen": p.origen_clasificacion,
                "duracion_min": round(p.duracion_segundos / 60),
            }
            for p in pausas_hoy
        ]

        eventos_hoy = db.eventos_del_dia(self._conn, hoy)

        ultimos_7 = [d["score"] for d in dias[-7:] if d["score"] is not None]
        todas_las_pausas_recientes = [
            p for r in resumenes for p in db.pausas_del_dia(self._conn, date.fromisoformat(r.fecha))
        ]
        confirmadas = sum(1 for p in todas_las_pausas_recientes if p.origen_clasificacion == "usuario")
        inferidas = sum(1 for p in todas_las_pausas_recientes if p.origen_clasificacion == "auto_inferido")

        return {
            "dias": dias,
            "pausas_hoy": pausas_serializadas,
            "entrada_hoy": next((e.timestamp.strftime("%H:%M") for e in eventos_hoy if e.tipo == "entrada"), None),
            "salida_hoy": next((e.timestamp.strftime("%H:%M") for e in eventos_hoy if e.tipo == "salida"), None),
            "score_semanal": calcular_score_semana(ultimos_7) if ultimos_7 else None,
            "pausas_confirmadas": confirmadas,
            "pausas_inferidas": inferidas,
        }

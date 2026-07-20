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
from control_horas.summary import calcular_entrada_efectiva

RUTA_HTML = Path(__file__).parent / "index.html"
DIAS_HISTORIAL = 60


class DashboardWindow(QWidget):
    def __init__(self, conn, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dashboard — Control de Horas")
        self.resize(1150, 780)
        self._conn = conn
        # La página web se carga de forma asíncrona; hasta que no termine, la
        # función window.renderDashboard() todavía no existe. Con esta bandera
        # evitamos inyectar datos antes de tiempo (si no, salta un error de JS
        # y el dashboard puede quedar en blanco un instante).
        self._pagina_cargada = False

        self._view = QWebEngineView(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._view)

        self._view.loadFinished.connect(self._on_load_finished)
        self._view.load(QUrl.fromLocalFile(str(RUTA_HTML)))

    def _on_load_finished(self, ok: bool) -> None:
        self._pagina_cargada = ok
        if ok:
            self.actualizar()

    def showEvent(self, event) -> None:  # noqa: N802 (override de Qt)
        super().showEvent(event)
        self.actualizar()

    def actualizar(self) -> None:
        if not self._pagina_cargada:
            # Todavía no cargó el HTML/JS; cuando termine, _on_load_finished
            # vuelve a llamar a actualizar() con los datos frescos.
            return
        datos = self._recolectar_datos()
        script = f"window.renderDashboard({json.dumps(datos)});"
        self._view.page().runJavaScript(script)

    def _recolectar_datos(self) -> dict:
        hoy = date.today()
        desde = hoy - timedelta(days=DIAS_HISTORIAL - 1)
        resumenes = db.resumenes_rango(self._conn, desde, hoy)
        config = db.get_config(self._conn)
        # Lunes de la semana en curso (weekday(): 0=lunes). Los cálculos de
        # semana toman solo desde este día en adelante.
        inicio_semana = hoy - timedelta(days=hoy.weekday())

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
                # Día marcado como laboral en la configuración (0=lunes). Los
                # cálculos de semana solo cuentan estos días.
                "laboral": date.fromisoformat(r.fecha).weekday() in config.dias_laborales,
                # ¿El día cae en la semana en curso (de lunes en adelante)?
                "semana_actual": date.fromisoformat(r.fecha) >= inicio_semana,
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
        entrada_efectiva = calcular_entrada_efectiva(eventos_hoy, pausas_hoy)

        # El score semanal promedia solo los días laborales de la semana en
        # curso (de lunes al día de hoy).
        scores_semana = [
            d["score"] for d in dias if d["score"] is not None and d["laboral"] and d["semana_actual"]
        ]
        todas_las_pausas_recientes = [
            p for r in resumenes for p in db.pausas_del_dia(self._conn, date.fromisoformat(r.fecha))
        ]
        confirmadas = sum(1 for p in todas_las_pausas_recientes if p.origen_clasificacion == "usuario")
        inferidas = sum(1 for p in todas_las_pausas_recientes if p.origen_clasificacion == "auto_inferido")

        return {
            "dias": dias,
            "pausas_hoy": pausas_serializadas,
            "entrada_hoy": entrada_efectiva.strftime("%H:%M") if entrada_efectiva else None,
            "salida_hoy": next((e.timestamp.strftime("%H:%M") for e in eventos_hoy if e.tipo == "salida"), None),
            "score_semanal": calcular_score_semana(scores_semana) if scores_semana else None,
            "pausas_confirmadas": confirmadas,
            "pausas_inferidas": inferidas,
        }

"""Punto de entrada: arranca la app en la bandeja del sistema y conecta todos
los componentes (detección de inactividad, popup de pausas, dashboard,
configuración y autoarranque)."""
from __future__ import annotations

import sys
from datetime import date, datetime

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from control_horas import autostart, db
from control_horas.classifier import clasificar_pausa
from control_horas.config_window import ConfigWindow
from control_horas.dashboard.window import DashboardWindow
from control_horas.idle_detector import IdleDetector
from control_horas.models import Config
from control_horas.pause_popup import PausePopup
from control_horas.summary import recalcular_resumen_dia
from control_horas.tray import SystemTray

INTERVALO_RECALCULO_RESUMEN_MS = 10 * 60 * 1000  # 10 minutos


class ControlHorasApp:
    def __init__(self, app: QApplication):
        self.app = app
        self.conn = db.connect()
        self.config: Config = db.get_config(self.conn)

        self._dashboard_window: DashboardWindow | None = None
        self._popup_actual: PausePopup | None = None
        self._pausa_actual_id: int | None = None
        self._pausa_actual_clasificacion: str | None = None

        self.tray = SystemTray(app)
        self.tray.entrada_manual_solicitada.connect(self._marcar_entrada_manual)
        self.tray.salida_manual_solicitada.connect(self._marcar_salida_manual)
        self.tray.pausa_manual_solicitada.connect(self._marcar_pausa_manual)
        self.tray.dashboard_solicitado.connect(self._mostrar_dashboard)
        self.tray.configuracion_solicitada.connect(self._mostrar_configuracion)
        self.tray.salir_solicitado.connect(self._salir)
        self.tray.show()

        self.idle_detector = IdleDetector(self.config.umbral_idle_minutos * 60)
        self.idle_detector.actividad_detectada.connect(self._on_actividad)
        self.idle_detector.pausa_iniciada.connect(self._on_pausa_iniciada)
        self.idle_detector.pausa_terminada.connect(self._on_pausa_terminada)
        self.idle_detector.start()

        self._timer_resumen = QTimer()
        self._timer_resumen.setInterval(INTERVALO_RECALCULO_RESUMEN_MS)
        self._timer_resumen.timeout.connect(self._recalcular_resumen_hoy)
        self._timer_resumen.start()

        try:
            autostart.registrar_si_hace_falta()
        except Exception:
            pass  # el autoarranque es best-effort; no debe impedir que la app corra

    # ------------------------------------------------------------- eventos

    def _on_actividad(self, ts: datetime) -> None:
        hoy = ts.date()
        if hoy.weekday() not in self.config.dias_laborales:
            return
        ya_hay_entrada = any(e.tipo == "entrada" for e in db.eventos_del_dia(self.conn, hoy))
        if not ya_hay_entrada:
            db.registrar_evento(self.conn, "entrada", origen="auto", timestamp=ts)
            self.tray.actualizar_estado(f"trabajando desde {ts.strftime('%H:%M')}")
            self.tray.notificar("Entrada registrada", f"Se marcó tu entrada a las {ts.strftime('%H:%M')}.")
            self._recalcular_resumen_hoy()

    def _on_pausa_iniciada(self, inicio: datetime) -> None:
        self._pausa_actual_id = db.iniciar_pausa(self.conn, inicio)
        self._pausa_actual_clasificacion = None
        self.tray.actualizar_estado(f"pausa desde {inicio.strftime('%H:%M')}")

        ya_hay_salida = any(e.tipo == "salida" for e in db.eventos_del_dia(self.conn, inicio.date()))
        if not ya_hay_salida and inicio.time() >= self.config.salida_esperada:
            # ya pasó la hora de salida esperada: tratamos esta pausa como fin de jornada
            db.registrar_evento(self.conn, "salida", origen="auto", timestamp=inicio)
            self.tray.notificar("Salida registrada", f"Se marcó tu salida a las {inicio.strftime('%H:%M')}.")
            self._recalcular_resumen_hoy()
            return

        self._mostrar_popup(inicio)

    def _on_pausa_terminada(self, inicio: datetime, fin: datetime) -> None:
        if self._pausa_actual_id is None:
            return

        if self._pausa_actual_clasificacion:
            clasificacion = self._pausa_actual_clasificacion
            origen = "usuario"
        else:
            clasificacion = clasificar_pausa(inicio, fin, self.config)
            origen = "auto_inferido"

        db.cerrar_pausa(self.conn, self._pausa_actual_id, fin, clasificacion, origen)

        if self._popup_actual is not None:
            self._popup_actual.cerrar_por_fin_de_pausa()
            self._popup_actual = None

        self._pausa_actual_id = None
        self._pausa_actual_clasificacion = None
        self.tray.actualizar_estado("trabajando")
        self._recalcular_resumen_hoy()

    # -------------------------------------------------------------- popup

    def _mostrar_popup(self, inicio: datetime) -> None:
        popup = PausePopup(inicio)
        popup.clasificado.connect(self._on_pausa_clasificada_por_usuario)
        popup.cerrado_sin_clasificar.connect(self._on_popup_cerrado_sin_clasificar)
        popup.show()
        self._popup_actual = popup

    def _on_pausa_clasificada_por_usuario(self, clasificacion: str) -> None:
        self._pausa_actual_clasificacion = clasificacion
        self._popup_actual = None

    def _on_popup_cerrado_sin_clasificar(self) -> None:
        # El usuario cerró el aviso sin elegir nada: la pausa se clasifica
        # sola por horario cuando termine (ver _on_pausa_terminada).
        self._popup_actual = None

    # ------------------------------------------------------- menú manual

    def _marcar_entrada_manual(self) -> None:
        db.registrar_evento(self.conn, "entrada", origen="manual")
        self.tray.notificar("Entrada marcada", "Marcaste tu entrada manualmente.")
        self._recalcular_resumen_hoy()

    def _marcar_salida_manual(self) -> None:
        db.registrar_evento(self.conn, "salida", origen="manual")
        self.tray.notificar("Salida marcada", "Marcaste tu salida manualmente.")
        self._recalcular_resumen_hoy()

    def _marcar_pausa_manual(self, tipo: str) -> None:
        if self._pausa_actual_id is None:
            self.tray.notificar("Sin pausa en curso", "No hay ninguna pausa activa para marcar.")
            return
        self._pausa_actual_clasificacion = tipo
        self.tray.notificar("Pausa clasificada", f"Se va a guardar como {tipo} cuando vuelvas a la compu.")

    # ---------------------------------------------------------- ventanas

    def _mostrar_dashboard(self) -> None:
        if self._dashboard_window is None:
            self._dashboard_window = DashboardWindow(self.conn)
        self._dashboard_window.show()
        self._dashboard_window.raise_()
        self._dashboard_window.activateWindow()

    def _mostrar_configuracion(self) -> None:
        dialogo = ConfigWindow(self.config)
        dialogo.configuracion_guardada.connect(self._guardar_configuracion)
        dialogo.exec()

    def _guardar_configuracion(self, nueva_config: Config) -> None:
        self.config = nueva_config
        db.save_config(self.conn, nueva_config)
        self.idle_detector.set_umbral_segundos(nueva_config.umbral_idle_minutos * 60)

    # ----------------------------------------------------------- resumen

    def _recalcular_resumen_hoy(self) -> None:
        recalcular_resumen_dia(self.conn, date.today(), self.config)
        if self._dashboard_window is not None and self._dashboard_window.isVisible():
            self._dashboard_window.actualizar()

    def _salir(self) -> None:
        self._recalcular_resumen_hoy()
        self.conn.close()
        self.app.quit()


def main() -> None:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    ControlHorasApp(app)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

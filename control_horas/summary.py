"""Recalcula y cachea el resumen diario (daily_summary) a partir de los
eventos y pausas crudas, aplicando el motor de scoring."""
from __future__ import annotations

from datetime import date, datetime

from control_horas import db
from control_horas.models import Config, ResumenDia
from control_horas.scoring import calcular_score_dia

SIN_CLASIFICAR_COMO_IDLE = {None, "sin_clasificar"}


def recalcular_resumen_dia(conn, fecha: date, config: Config) -> ResumenDia:
    """Lee eventos/pausas del día, recalcula segundos trabajados y el score,
    y deja el resultado guardado en `daily_summary`."""
    eventos = db.eventos_del_dia(conn, fecha)
    pausas = db.pausas_del_dia(conn, fecha)

    entrada = next((e.timestamp for e in eventos if e.tipo == "entrada"), None)
    salida = next((e.timestamp for e in reversed(eventos) if e.tipo == "salida"), None)

    duracion_almuerzo_seg = sum(p.duracion_segundos for p in pausas if p.clasificacion == "almuerzo")
    duracion_merienda_seg = sum(p.duracion_segundos for p in pausas if p.clasificacion == "merienda")
    segundos_idle_sin_clasificar = sum(
        p.duracion_segundos for p in pausas if p.clasificacion in SIN_CLASIFICAR_COMO_IDLE
    )
    total_pausas_seg = sum(p.duracion_segundos for p in pausas)

    fin_referencia = salida or datetime.now()
    segundos_trabajados = 0
    if entrada is not None:
        segundos_trabajados = max(0, int((fin_referencia - entrada).total_seconds()) - total_pausas_seg)

    resumen = ResumenDia(
        fecha=fecha.isoformat(),
        entrada=entrada,
        salida=salida,
        duracion_almuerzo_seg=duracion_almuerzo_seg,
        duracion_merienda_seg=duracion_merienda_seg,
        segundos_trabajados=segundos_trabajados,
        segundos_idle_sin_clasificar=segundos_idle_sin_clasificar,
    )
    resumen.score = calcular_score_dia(resumen, config) if entrada is not None else None

    db.guardar_resumen_dia(conn, resumen)
    return resumen

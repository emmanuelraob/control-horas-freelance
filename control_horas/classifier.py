"""Infiere la clasificación de una pausa (idle period) cuando el usuario
no respondió el popup, comparando el horario real contra las ventanas
configuradas (almuerzo / merienda)."""
from __future__ import annotations

from datetime import datetime, time

from control_horas.models import Config

ALMUERZO = "almuerzo"
MERIENDA = "merienda"
BAÑO = "baño"
OTRA_COSA = "otra_cosa"
SIN_CLASIFICAR = "sin_clasificar"


def _punto_medio(inicio: datetime, fin: datetime) -> time:
    return (inicio + (fin - inicio) / 2).time()


def _dentro_de_ventana(inicio: datetime, fin: datetime, v_inicio: time, v_fin: time) -> bool:
    return v_inicio <= _punto_medio(inicio, fin) <= v_fin


def clasificar_pausa(inicio: datetime, fin: datetime, config: Config) -> str:
    """Devuelve almuerzo/merienda/otra_cosa/sin_clasificar según en qué
    ventana horaria configurada cae el punto medio de la pausa."""
    if _dentro_de_ventana(inicio, fin, config.ventana_almuerzo_inicio, config.ventana_almuerzo_fin):
        return ALMUERZO

    for v_inicio, v_fin in config.ventanas_merienda:
        if _dentro_de_ventana(inicio, fin, v_inicio, v_fin):
            return MERIENDA

    duracion_min = (fin - inicio).total_seconds() / 60
    if duracion_min <= config.duracion_maxima_pausa_corta_min:
        return OTRA_COSA

    return SIN_CLASIFICAR

from datetime import datetime, time

from control_horas.classifier import (
    ALMUERZO,
    MERIENDA,
    OTRA_COSA,
    SIN_CLASIFICAR,
    clasificar_pausa,
)
from control_horas.models import Config


def _config():
    return Config(
        ventana_almuerzo_inicio=time(12, 0),
        ventana_almuerzo_fin=time(14, 30),
        ventanas_merienda=[(time(9, 30), time(10, 0))],
        duracion_maxima_pausa_corta_min=15,
    )


def test_pausa_dentro_de_ventana_de_almuerzo():
    inicio = datetime(2026, 7, 20, 13, 0)
    fin = datetime(2026, 7, 20, 14, 0)
    assert clasificar_pausa(inicio, fin, _config()) == ALMUERZO


def test_pausa_dentro_de_ventana_de_merienda():
    inicio = datetime(2026, 7, 20, 9, 35)
    fin = datetime(2026, 7, 20, 9, 50)
    assert clasificar_pausa(inicio, fin, _config()) == MERIENDA


def test_pausa_corta_fuera_de_ventanas_es_otra_cosa():
    inicio = datetime(2026, 7, 20, 11, 0)
    fin = datetime(2026, 7, 20, 11, 10)
    assert clasificar_pausa(inicio, fin, _config()) == OTRA_COSA


def test_pausa_larga_fuera_de_ventanas_queda_sin_clasificar():
    inicio = datetime(2026, 7, 20, 16, 0)
    fin = datetime(2026, 7, 20, 16, 45)
    assert clasificar_pausa(inicio, fin, _config()) == SIN_CLASIFICAR


def test_usa_el_punto_medio_de_la_pausa():
    # empieza justo antes de la ventana de almuerzo pero el punto medio cae dentro
    inicio = datetime(2026, 7, 20, 11, 50)
    fin = datetime(2026, 7, 20, 12, 20)
    assert clasificar_pausa(inicio, fin, _config()) == ALMUERZO

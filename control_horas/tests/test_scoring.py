from datetime import datetime, time

from control_horas.models import Config, ResumenDia
from control_horas.scoring import (
    calcular_score_dia,
    calcular_score_semana,
    score_actividad,
    score_duracion_pausa,
    score_horas_trabajadas,
    score_puntualidad_entrada,
    score_puntualidad_salida,
)


def _config():
    return Config(
        entrada_esperada=time(9, 0),
        salida_esperada=time(18, 0),
        tolerancia_minutos=10,
        duracion_esperada_almuerzo_min=60,
        duracion_esperada_merienda_min=15,
    )


def test_entrada_puntual_da_score_maximo():
    entrada = datetime(2026, 7, 20, 9, 5)
    assert score_puntualidad_entrada(entrada, _config()) == 100.0


def test_entrada_tarde_penaliza_proporcionalmente():
    entrada = datetime(2026, 7, 20, 9, 30)  # 20 min tarde, 10 de tolerancia -> 10 de exceso
    score = score_puntualidad_entrada(entrada, _config())
    assert 0 < score < 100


def test_sin_entrada_score_cero():
    assert score_puntualidad_entrada(None, _config()) == 0.0


def test_salida_antes_de_hora_penaliza():
    salida = datetime(2026, 7, 20, 17, 0)  # se fue 1 hora antes
    score = score_puntualidad_salida(salida, _config())
    assert score < 100


def test_salida_a_horario_da_score_maximo():
    salida = datetime(2026, 7, 20, 18, 5)
    assert score_puntualidad_salida(salida, _config()) == 100.0


def test_duracion_pausa_dentro_de_tolerancia():
    assert score_duracion_pausa(60 * 60, duracion_esperada_min=60) == 100.0


def test_duracion_pausa_muy_larga_penaliza():
    score = score_duracion_pausa(150 * 60, duracion_esperada_min=60)
    assert score < 100


def test_horas_trabajadas_completas():
    assert score_horas_trabajadas(8 * 3600, 8 * 3600) == 100.0


def test_horas_trabajadas_parciales():
    assert score_horas_trabajadas(4 * 3600, 8 * 3600) == 50.0


def test_actividad_sin_idle_es_maxima():
    assert score_actividad(8 * 3600, 0) == 100.0


def test_actividad_con_mucho_idle_baja():
    assert score_actividad(8 * 3600, 4 * 3600) == 50.0


def test_calcular_score_dia_jornada_perfecta():
    config = _config()
    resumen = ResumenDia(
        fecha="2026-07-20",
        entrada=datetime(2026, 7, 20, 9, 0),
        salida=datetime(2026, 7, 20, 18, 0),
        duracion_almuerzo_seg=60 * 60,
        duracion_merienda_seg=15 * 60,
        segundos_trabajados=int((datetime(2026, 7, 20, 18, 0) - datetime(2026, 7, 20, 9, 0)).total_seconds())
        - 75 * 60,
        segundos_idle_sin_clasificar=0,
    )
    score = calcular_score_dia(resumen, config)
    assert score == 100.0


def test_calcular_score_dia_sin_venir_es_muy_bajo():
    resumen = ResumenDia(fecha="2026-07-20")
    assert calcular_score_dia(resumen, _config()) < 10.0


def test_calcular_score_semana_promedia_dias_validos():
    assert calcular_score_semana([100.0, 80.0, None, 60.0]) == 80.0


def test_calcular_score_semana_sin_datos_es_cero():
    assert calcular_score_semana([None, None]) == 0.0

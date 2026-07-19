"""Motor de calificación (0-100) de cumplimiento de horario, por día y por semana."""
from __future__ import annotations

from datetime import date, datetime

from control_horas.models import Config, ResumenDia

PESOS = {
    "entrada": 0.25,
    "salida": 0.20,
    "horas_trabajadas": 0.20,
    "almuerzo": 0.15,
    "merienda": 0.10,
    "actividad": 0.10,
}


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def score_puntualidad_entrada(
    entrada: datetime | None, config: Config, penalizacion_por_minuto: float = 4.0
) -> float:
    if entrada is None:
        return 0.0
    esperada = datetime.combine(entrada.date(), config.entrada_esperada)
    minutos_tarde = (entrada - esperada).total_seconds() / 60
    if minutos_tarde <= config.tolerancia_minutos:
        return 100.0
    exceso = minutos_tarde - config.tolerancia_minutos
    return _clamp(100 - exceso * penalizacion_por_minuto)


def score_puntualidad_salida(
    salida: datetime | None, config: Config, penalizacion_por_minuto: float = 4.0
) -> float:
    if salida is None:
        return 0.0
    esperada = datetime.combine(salida.date(), config.salida_esperada)
    minutos_antes = (esperada - salida).total_seconds() / 60
    if minutos_antes <= config.tolerancia_minutos:
        return 100.0
    exceso = minutos_antes - config.tolerancia_minutos
    return _clamp(100 - exceso * penalizacion_por_minuto)


def score_duracion_pausa(
    duracion_segundos: int,
    duracion_esperada_min: int,
    tolerancia_min: int = 10,
    penalizacion_por_minuto: float = 5.0,
) -> float:
    if duracion_esperada_min <= 0:
        return 100.0
    duracion_min = duracion_segundos / 60
    diferencia = abs(duracion_min - duracion_esperada_min)
    if diferencia <= tolerancia_min:
        return 100.0
    exceso = diferencia - tolerancia_min
    return _clamp(100 - exceso * penalizacion_por_minuto)


def score_horas_trabajadas(segundos_trabajados: int, segundos_esperados: int) -> float:
    if segundos_esperados <= 0:
        return 100.0
    return _clamp(segundos_trabajados / segundos_esperados * 100)


def score_actividad(segundos_trabajados: int, segundos_idle_sin_clasificar: int) -> float:
    if segundos_trabajados <= 0:
        return 0.0
    return _clamp((segundos_trabajados - segundos_idle_sin_clasificar) / segundos_trabajados * 100)


def _segundos_esperados_jornada(config: Config) -> int:
    jornada = datetime.combine(date.min, config.salida_esperada) - datetime.combine(
        date.min, config.entrada_esperada
    )
    pausas = config.duracion_esperada_almuerzo_min + config.duracion_esperada_merienda_min
    return max(0, int(jornada.total_seconds()) - pausas * 60)


def calcular_score_dia(resumen: ResumenDia, config: Config) -> float:
    segundos_esperados = _segundos_esperados_jornada(config)
    subscores = {
        "entrada": score_puntualidad_entrada(resumen.entrada, config),
        "salida": score_puntualidad_salida(resumen.salida, config),
        "horas_trabajadas": score_horas_trabajadas(resumen.segundos_trabajados, segundos_esperados),
        "almuerzo": score_duracion_pausa(
            resumen.duracion_almuerzo_seg, config.duracion_esperada_almuerzo_min
        ),
        "merienda": score_duracion_pausa(
            resumen.duracion_merienda_seg, config.duracion_esperada_merienda_min
        ),
        "actividad": score_actividad(
            resumen.segundos_trabajados, resumen.segundos_idle_sin_clasificar
        ),
    }
    total = sum(subscores[factor] * peso for factor, peso in PESOS.items())
    return round(_clamp(total), 1)


def calcular_score_semana(scores_diarios: list[float | None]) -> float:
    dias_validos = [s for s in scores_diarios if s is not None]
    if not dias_validos:
        return 0.0
    return round(sum(dias_validos) / len(dias_validos), 1)

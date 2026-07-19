"""Genera datos falsos (últimas 2 semanas) en la base de datos real de la app
(la misma que usa `python -m control_horas.main`), solo para poder ver el
dashboard con información de prueba. No toca el día de hoy, para no chocar
con lo que la app esté registrando en vivo.

Uso:
    python3 scripts/seed_datos_prueba.py
"""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta

from control_horas import db, summary
from control_horas.models import Config

DIAS_A_GENERAR = 14


def _hora_con_variacion(fecha: date, hora_base, minutos_variacion: tuple[int, int]) -> datetime:
    base = datetime.combine(fecha, hora_base)
    return base + timedelta(minutes=random.randint(*minutos_variacion))


def generar_dia(conn, fecha: date, config: Config) -> bool:
    if db.eventos_del_dia(conn, fecha):
        print(f"  {fecha.isoformat()} ya tiene datos, se salta (correr solo una vez)")
        return False

    entrada = _hora_con_variacion(fecha, config.entrada_esperada, (-5, 22))
    salida = _hora_con_variacion(fecha, config.salida_esperada, (-25, 15))

    db.registrar_evento(conn, "entrada", origen=random.choice(["auto", "auto", "auto", "manual"]), timestamp=entrada)
    db.registrar_evento(conn, "salida", origen=random.choice(["auto", "auto", "auto", "manual"]), timestamp=salida)

    # Almuerzo: casi siempre, con duración cerca de la esperada
    inicio_almuerzo = _hora_con_variacion(fecha, config.ventana_almuerzo_inicio, (0, 45))
    duracion_almuerzo = config.duracion_esperada_almuerzo_min + random.randint(-10, 25)
    fin_almuerzo = inicio_almuerzo + timedelta(minutes=max(15, duracion_almuerzo))
    origen_almuerzo = random.choice(["usuario", "usuario", "auto_inferido"])
    pausa_id = db.iniciar_pausa(conn, inicio_almuerzo)
    db.cerrar_pausa(conn, pausa_id, fin_almuerzo, clasificacion="almuerzo", origen_clasificacion=origen_almuerzo)

    # Merienda: casi siempre, si hay ventana configurada
    if config.ventanas_merienda:
        v_inicio, _ = config.ventanas_merienda[0]
        inicio_merienda = _hora_con_variacion(fecha, v_inicio, (0, 10))
        duracion_merienda = config.duracion_esperada_merienda_min + random.randint(-5, 10)
        fin_merienda = inicio_merienda + timedelta(minutes=max(5, duracion_merienda))
        origen_merienda = random.choice(["usuario", "auto_inferido"])
        pausa_id = db.iniciar_pausa(conn, inicio_merienda)
        db.cerrar_pausa(conn, pausa_id, fin_merienda, clasificacion="merienda", origen_clasificacion=origen_merienda)

    punto_medio = entrada + (salida - entrada) / 2

    # Pausa corta ocasional (baño / otra cosa), cerca de la mitad de la jornada
    if random.random() < 0.6:
        inicio_corta = punto_medio + timedelta(minutes=random.randint(-90, 90))
        duracion_corta = random.randint(3, config.duracion_maxima_pausa_corta_min)
        fin_corta = inicio_corta + timedelta(minutes=duracion_corta)
        clasificacion_corta = random.choice(["baño", "otra_cosa"])
        pausa_id = db.iniciar_pausa(conn, inicio_corta)
        db.cerrar_pausa(conn, pausa_id, fin_corta, clasificacion=clasificacion_corta, origen_clasificacion="auto_inferido")

    # De vez en cuando, una pausa larga sin clasificar (para mostrar el caso "a revisar")
    if random.random() < 0.2:
        inicio_sc = salida - timedelta(minutes=random.randint(90, 180))
        fin_sc = inicio_sc + timedelta(minutes=random.randint(20, 40))
        pausa_id = db.iniciar_pausa(conn, inicio_sc)
        db.cerrar_pausa(conn, pausa_id, fin_sc, clasificacion="sin_clasificar", origen_clasificacion="auto_inferido")

    summary.recalcular_resumen_dia(conn, fecha, config)
    return True


def main() -> None:
    random.seed(7)
    conn = db.connect()
    config = db.get_config(conn)

    hoy = date.today()
    generados = 0
    for offset in range(1, DIAS_A_GENERAR + 1):
        fecha = hoy - timedelta(days=offset)
        if fecha.weekday() not in config.dias_laborales:
            continue
        if generar_dia(conn, fecha, config):
            generados += 1
            print(f"  {fecha.isoformat()} ({fecha.strftime('%A')}) OK")

    conn.close()
    print(f"\nListo: {generados} días de datos de prueba generados en {db.get_db_path()}")


if __name__ == "__main__":
    main()

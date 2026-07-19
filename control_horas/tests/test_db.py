from datetime import date, datetime, time

import pytest

from control_horas import db
from control_horas.models import Config, ResumenDia


@pytest.fixture
def conn():
    connection = db.connect(":memory:")
    yield connection
    connection.close()


def test_config_por_defecto_se_crea_sola(conn):
    config = db.get_config(conn)
    assert config.entrada_esperada == time(9, 0)
    assert config.dias_laborales == [0, 1, 2, 3, 4]


def test_guardar_y_leer_config(conn):
    nueva = Config(
        entrada_esperada=time(8, 30),
        salida_esperada=time(17, 30),
        ventanas_merienda=[(time(9, 0), time(9, 20)), (time(16, 0), time(16, 15))],
    )
    db.save_config(conn, nueva)
    leida = db.get_config(conn)
    assert leida.entrada_esperada == time(8, 30)
    assert leida.salida_esperada == time(17, 30)
    assert leida.ventanas_merienda == [(time(9, 0), time(9, 20)), (time(16, 0), time(16, 15))]


def test_registrar_y_leer_eventos_del_dia(conn):
    hoy = datetime(2026, 7, 20, 9, 0)
    db.registrar_evento(conn, "entrada", origen="auto", timestamp=hoy)
    db.registrar_evento(conn, "salida", origen="auto", timestamp=hoy.replace(hour=18))

    eventos = db.eventos_del_dia(conn, date(2026, 7, 20))
    assert [e.tipo for e in eventos] == ["entrada", "salida"]
    assert db.ultimo_evento(conn).tipo == "salida"


def test_ciclo_de_vida_de_una_pausa(conn):
    inicio = datetime(2026, 7, 20, 12, 0)
    pausa_id = db.iniciar_pausa(conn, inicio)

    assert db.pausa_abierta(conn).id == pausa_id

    fin = datetime(2026, 7, 20, 13, 0)
    db.cerrar_pausa(conn, pausa_id, fin, clasificacion="almuerzo", origen_clasificacion="auto_inferido")

    assert db.pausa_abierta(conn) is None
    pausas = db.pausas_del_dia(conn, date(2026, 7, 20))
    assert len(pausas) == 1
    assert pausas[0].clasificacion == "almuerzo"
    assert pausas[0].duracion_segundos == 3600


def test_resumen_diario_se_guarda_y_se_actualiza(conn):
    resumen = ResumenDia(fecha="2026-07-20", segundos_trabajados=1000, score=80.0)
    db.guardar_resumen_dia(conn, resumen)

    guardado = db.resumen_dia(conn, date(2026, 7, 20))
    assert guardado.score == 80.0

    resumen.score = 95.0
    db.guardar_resumen_dia(conn, resumen)
    actualizado = db.resumen_dia(conn, date(2026, 7, 20))
    assert actualizado.score == 95.0


def test_resumenes_rango(conn):
    for dia, score in [(18, 70.0), (19, 80.0), (20, 90.0)]:
        db.guardar_resumen_dia(conn, ResumenDia(fecha=f"2026-07-{dia}", score=score))

    resultados = db.resumenes_rango(conn, date(2026, 7, 18), date(2026, 7, 19))
    assert [r.score for r in resultados] == [70.0, 80.0]

from datetime import date, datetime, time

import pytest

from control_horas import db
from control_horas.models import Config
from control_horas.summary import recalcular_resumen_dia


@pytest.fixture
def conn():
    connection = db.connect(":memory:")
    yield connection
    connection.close()


def _config():
    return Config(entrada_esperada=time(9, 0), salida_esperada=time(18, 0))


def test_dia_sin_eventos_no_tiene_score(conn):
    resumen = recalcular_resumen_dia(conn, date(2026, 7, 20), _config())
    assert resumen.entrada is None
    assert resumen.score is None


def test_jornada_completa_con_almuerzo(conn):
    fecha = date(2026, 7, 20)
    db.registrar_evento(conn, "entrada", timestamp=datetime(2026, 7, 20, 9, 0))
    db.registrar_evento(conn, "salida", timestamp=datetime(2026, 7, 20, 18, 0))

    pausa_id = db.iniciar_pausa(conn, datetime(2026, 7, 20, 12, 0))
    db.cerrar_pausa(
        conn,
        pausa_id,
        datetime(2026, 7, 20, 13, 0),
        clasificacion="almuerzo",
        origen_clasificacion="auto_inferido",
    )

    resumen = recalcular_resumen_dia(conn, fecha, _config())

    assert resumen.duracion_almuerzo_seg == 3600
    assert resumen.segundos_trabajados == int((datetime(2026, 7, 20, 18, 0) - datetime(2026, 7, 20, 9, 0)).total_seconds()) - 3600
    assert resumen.score is not None
    assert resumen.score > 0

    guardado = db.resumen_dia(conn, fecha)
    assert guardado.score == resumen.score


def test_sin_entrada_usa_primera_hora_de_uso(conn):
    """Si no hay evento de entrada, la entrada cae a la primera hora de uso
    de la compu ese día (inicio de la primera pausa registrada)."""
    fecha = date(2026, 7, 20)

    pausa_id = db.iniciar_pausa(conn, datetime(2026, 7, 20, 10, 30))
    db.cerrar_pausa(conn, pausa_id, datetime(2026, 7, 20, 10, 45), clasificacion="baño")
    pausa2 = db.iniciar_pausa(conn, datetime(2026, 7, 20, 13, 0))
    db.cerrar_pausa(conn, pausa2, datetime(2026, 7, 20, 13, 30), clasificacion="almuerzo")

    resumen = recalcular_resumen_dia(conn, fecha, _config())

    assert resumen.entrada == datetime(2026, 7, 20, 10, 30)
    assert resumen.score is not None


def test_pausa_sin_clasificar_cuenta_como_idle(conn):
    fecha = date(2026, 7, 20)
    db.registrar_evento(conn, "entrada", timestamp=datetime(2026, 7, 20, 9, 0))

    pausa_id = db.iniciar_pausa(conn, datetime(2026, 7, 20, 16, 0))
    db.cerrar_pausa(conn, pausa_id, datetime(2026, 7, 20, 16, 45), clasificacion="sin_clasificar")

    resumen = recalcular_resumen_dia(conn, fecha, _config())
    assert resumen.segundos_idle_sin_clasificar == 45 * 60

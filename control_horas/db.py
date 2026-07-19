"""Acceso a la base de datos SQLite local: eventos, pausas, resúmenes diarios y configuración."""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import date, datetime, time
from pathlib import Path

from control_horas.models import Config, Evento, IdlePeriod, ResumenDia

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    tipo TEXT NOT NULL,
    origen TEXT NOT NULL DEFAULT 'auto'
);

CREATE TABLE IF NOT EXISTS idle_periods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inicio TEXT NOT NULL,
    fin TEXT,
    clasificacion TEXT,
    origen_clasificacion TEXT
);

CREATE TABLE IF NOT EXISTS daily_summary (
    fecha TEXT PRIMARY KEY,
    entrada TEXT,
    salida TEXT,
    duracion_almuerzo_seg INTEGER NOT NULL DEFAULT 0,
    duracion_merienda_seg INTEGER NOT NULL DEFAULT 0,
    segundos_trabajados INTEGER NOT NULL DEFAULT 0,
    segundos_idle_sin_clasificar INTEGER NOT NULL DEFAULT 0,
    score REAL,
    flags TEXT
);

CREATE TABLE IF NOT EXISTS config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    entrada_esperada TEXT NOT NULL,
    salida_esperada TEXT NOT NULL,
    tolerancia_minutos INTEGER NOT NULL,
    ventana_almuerzo_inicio TEXT NOT NULL,
    ventana_almuerzo_fin TEXT NOT NULL,
    duracion_esperada_almuerzo_min INTEGER NOT NULL,
    ventanas_merienda TEXT NOT NULL,
    duracion_esperada_merienda_min INTEGER NOT NULL,
    dias_laborales TEXT NOT NULL,
    umbral_idle_minutos INTEGER NOT NULL,
    duracion_maxima_pausa_corta_min INTEGER NOT NULL
);
"""


def get_db_path() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    directorio = Path(base) / "ControlHoras" if base else Path.home() / ".control_horas"
    directorio.mkdir(parents=True, exist_ok=True)
    return directorio / "data.db"


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_schema(conn)
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    if conn.execute("SELECT 1 FROM config WHERE id = 1").fetchone() is None:
        save_config(conn, Config())
    conn.commit()


# ---------------------------------------------------------------- config ---

def _time_to_str(t: time) -> str:
    return t.strftime("%H:%M")


def _str_to_time(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))


def get_config(conn: sqlite3.Connection) -> Config:
    row = conn.execute("SELECT * FROM config WHERE id = 1").fetchone()
    if row is None:
        return Config()
    ventanas_merienda = [
        (_str_to_time(a), _str_to_time(b)) for a, b in json.loads(row["ventanas_merienda"])
    ]
    return Config(
        entrada_esperada=_str_to_time(row["entrada_esperada"]),
        salida_esperada=_str_to_time(row["salida_esperada"]),
        tolerancia_minutos=row["tolerancia_minutos"],
        ventana_almuerzo_inicio=_str_to_time(row["ventana_almuerzo_inicio"]),
        ventana_almuerzo_fin=_str_to_time(row["ventana_almuerzo_fin"]),
        duracion_esperada_almuerzo_min=row["duracion_esperada_almuerzo_min"],
        ventanas_merienda=ventanas_merienda,
        duracion_esperada_merienda_min=row["duracion_esperada_merienda_min"],
        dias_laborales=json.loads(row["dias_laborales"]),
        umbral_idle_minutos=row["umbral_idle_minutos"],
        duracion_maxima_pausa_corta_min=row["duracion_maxima_pausa_corta_min"],
    )


def save_config(conn: sqlite3.Connection, config: Config) -> None:
    ventanas_merienda = json.dumps(
        [[_time_to_str(a), _time_to_str(b)] for a, b in config.ventanas_merienda]
    )
    conn.execute(
        """
        INSERT INTO config (
            id, entrada_esperada, salida_esperada, tolerancia_minutos,
            ventana_almuerzo_inicio, ventana_almuerzo_fin, duracion_esperada_almuerzo_min,
            ventanas_merienda, duracion_esperada_merienda_min, dias_laborales,
            umbral_idle_minutos, duracion_maxima_pausa_corta_min
        ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            entrada_esperada=excluded.entrada_esperada,
            salida_esperada=excluded.salida_esperada,
            tolerancia_minutos=excluded.tolerancia_minutos,
            ventana_almuerzo_inicio=excluded.ventana_almuerzo_inicio,
            ventana_almuerzo_fin=excluded.ventana_almuerzo_fin,
            duracion_esperada_almuerzo_min=excluded.duracion_esperada_almuerzo_min,
            ventanas_merienda=excluded.ventanas_merienda,
            duracion_esperada_merienda_min=excluded.duracion_esperada_merienda_min,
            dias_laborales=excluded.dias_laborales,
            umbral_idle_minutos=excluded.umbral_idle_minutos,
            duracion_maxima_pausa_corta_min=excluded.duracion_maxima_pausa_corta_min
        """,
        (
            _time_to_str(config.entrada_esperada),
            _time_to_str(config.salida_esperada),
            config.tolerancia_minutos,
            _time_to_str(config.ventana_almuerzo_inicio),
            _time_to_str(config.ventana_almuerzo_fin),
            config.duracion_esperada_almuerzo_min,
            ventanas_merienda,
            config.duracion_esperada_merienda_min,
            json.dumps(config.dias_laborales),
            config.umbral_idle_minutos,
            config.duracion_maxima_pausa_corta_min,
        ),
    )
    conn.commit()


# ---------------------------------------------------------------- events ---

def registrar_evento(
    conn: sqlite3.Connection, tipo: str, origen: str = "auto", timestamp: datetime | None = None
) -> int:
    timestamp = timestamp or datetime.now()
    cur = conn.execute(
        "INSERT INTO events (timestamp, tipo, origen) VALUES (?, ?, ?)",
        (timestamp.isoformat(), tipo, origen),
    )
    conn.commit()
    return cur.lastrowid


def eventos_del_dia(conn: sqlite3.Connection, fecha: date) -> list[Evento]:
    rows = conn.execute(
        "SELECT * FROM events WHERE date(timestamp) = ? ORDER BY timestamp", (fecha.isoformat(),)
    ).fetchall()
    return [
        Evento(id=r["id"], timestamp=datetime.fromisoformat(r["timestamp"]), tipo=r["tipo"], origen=r["origen"])
        for r in rows
    ]


def ultimo_evento(conn: sqlite3.Connection) -> Evento | None:
    row = conn.execute("SELECT * FROM events ORDER BY timestamp DESC LIMIT 1").fetchone()
    if row is None:
        return None
    return Evento(id=row["id"], timestamp=datetime.fromisoformat(row["timestamp"]), tipo=row["tipo"], origen=row["origen"])


# ---------------------------------------------------------- idle periods ---

def iniciar_pausa(conn: sqlite3.Connection, inicio: datetime) -> int:
    cur = conn.execute("INSERT INTO idle_periods (inicio) VALUES (?)", (inicio.isoformat(),))
    conn.commit()
    return cur.lastrowid


def cerrar_pausa(
    conn: sqlite3.Connection,
    pausa_id: int,
    fin: datetime,
    clasificacion: str | None = None,
    origen_clasificacion: str | None = None,
) -> None:
    conn.execute(
        "UPDATE idle_periods SET fin = ?, clasificacion = ?, origen_clasificacion = ? WHERE id = ?",
        (fin.isoformat(), clasificacion, origen_clasificacion, pausa_id),
    )
    conn.commit()


def clasificar_pausa_guardada(
    conn: sqlite3.Connection, pausa_id: int, clasificacion: str, origen_clasificacion: str
) -> None:
    conn.execute(
        "UPDATE idle_periods SET clasificacion = ?, origen_clasificacion = ? WHERE id = ?",
        (clasificacion, origen_clasificacion, pausa_id),
    )
    conn.commit()


def pausa_abierta(conn: sqlite3.Connection) -> IdlePeriod | None:
    row = conn.execute("SELECT * FROM idle_periods WHERE fin IS NULL ORDER BY inicio DESC LIMIT 1").fetchone()
    return _row_to_idle_period(row) if row else None


def pausas_del_dia(conn: sqlite3.Connection, fecha: date) -> list[IdlePeriod]:
    rows = conn.execute(
        "SELECT * FROM idle_periods WHERE date(inicio) = ? ORDER BY inicio", (fecha.isoformat(),)
    ).fetchall()
    return [_row_to_idle_period(r) for r in rows]


def _row_to_idle_period(row: sqlite3.Row) -> IdlePeriod:
    return IdlePeriod(
        id=row["id"],
        inicio=datetime.fromisoformat(row["inicio"]),
        fin=datetime.fromisoformat(row["fin"]) if row["fin"] else None,
        clasificacion=row["clasificacion"],
        origen_clasificacion=row["origen_clasificacion"],
    )


# --------------------------------------------------------- daily summary ---

def guardar_resumen_dia(conn: sqlite3.Connection, resumen: ResumenDia) -> None:
    conn.execute(
        """
        INSERT INTO daily_summary (
            fecha, entrada, salida, duracion_almuerzo_seg, duracion_merienda_seg,
            segundos_trabajados, segundos_idle_sin_clasificar, score, flags
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(fecha) DO UPDATE SET
            entrada=excluded.entrada,
            salida=excluded.salida,
            duracion_almuerzo_seg=excluded.duracion_almuerzo_seg,
            duracion_merienda_seg=excluded.duracion_merienda_seg,
            segundos_trabajados=excluded.segundos_trabajados,
            segundos_idle_sin_clasificar=excluded.segundos_idle_sin_clasificar,
            score=excluded.score,
            flags=excluded.flags
        """,
        (
            resumen.fecha,
            resumen.entrada.isoformat() if resumen.entrada else None,
            resumen.salida.isoformat() if resumen.salida else None,
            resumen.duracion_almuerzo_seg,
            resumen.duracion_merienda_seg,
            resumen.segundos_trabajados,
            resumen.segundos_idle_sin_clasificar,
            resumen.score,
            json.dumps(resumen.flags),
        ),
    )
    conn.commit()


def resumen_dia(conn: sqlite3.Connection, fecha: date) -> ResumenDia | None:
    row = conn.execute("SELECT * FROM daily_summary WHERE fecha = ?", (fecha.isoformat(),)).fetchone()
    return _row_to_resumen(row) if row else None


def resumenes_rango(conn: sqlite3.Connection, fecha_inicio: date, fecha_fin: date) -> list[ResumenDia]:
    rows = conn.execute(
        "SELECT * FROM daily_summary WHERE fecha BETWEEN ? AND ? ORDER BY fecha",
        (fecha_inicio.isoformat(), fecha_fin.isoformat()),
    ).fetchall()
    return [_row_to_resumen(r) for r in rows]


def _row_to_resumen(row: sqlite3.Row) -> ResumenDia:
    return ResumenDia(
        fecha=row["fecha"],
        entrada=datetime.fromisoformat(row["entrada"]) if row["entrada"] else None,
        salida=datetime.fromisoformat(row["salida"]) if row["salida"] else None,
        duracion_almuerzo_seg=row["duracion_almuerzo_seg"],
        duracion_merienda_seg=row["duracion_merienda_seg"],
        segundos_trabajados=row["segundos_trabajados"],
        segundos_idle_sin_clasificar=row["segundos_idle_sin_clasificar"],
        score=row["score"],
        flags=json.loads(row["flags"]) if row["flags"] else [],
    )

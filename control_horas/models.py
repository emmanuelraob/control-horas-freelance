"""Estructuras de datos compartidas entre db, classifier y scoring."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Optional


@dataclass
class Config:
    entrada_esperada: time = time(6, 0)
    salida_esperada: time = time(15, 15)
    tolerancia_minutos: int = 10

    ventana_almuerzo_inicio: time = time(12, 0)
    ventana_almuerzo_fin: time = time(14, 30)
    # 0 = la jornada no incluye almuerzo: no se descuenta de las horas
    # esperadas ni se penaliza en el score (ver scoring._segundos_esperados_jornada
    # y score_duracion_pausa).
    duracion_esperada_almuerzo_min: int = 0

    ventanas_merienda: list[tuple[time, time]] = field(
        default_factory=lambda: [(time(9, 30), time(10, 0))]
    )
    duracion_esperada_merienda_min: int = 15

    dias_laborales: list[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])  # 0=lunes

    umbral_idle_minutos: int = 5
    duracion_maxima_pausa_corta_min: int = 15


@dataclass
class Evento:
    timestamp: datetime
    tipo: str  # "entrada" | "salida"
    origen: str = "auto"  # "auto" | "manual"
    id: Optional[int] = None


@dataclass
class IdlePeriod:
    inicio: datetime
    fin: Optional[datetime] = None
    clasificacion: Optional[str] = None  # almuerzo|merienda|otra_cosa|sin_clasificar
    origen_clasificacion: Optional[str] = None  # usuario|auto_inferido
    id: Optional[int] = None

    @property
    def duracion_segundos(self) -> int:
        if self.fin is None:
            return 0
        return int((self.fin - self.inicio).total_seconds())


@dataclass
class ResumenDia:
    fecha: str
    entrada: Optional[datetime] = None
    salida: Optional[datetime] = None
    duracion_almuerzo_seg: int = 0
    duracion_merienda_seg: int = 0
    segundos_trabajados: int = 0
    segundos_idle_sin_clasificar: int = 0
    score: Optional[float] = None
    flags: list[str] = field(default_factory=list)

"""Contrato de estadísticas adaptado de Hito 11 (ver docs/procedencia.md)."""
from datetime import timezone
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

Code = Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
MatchID = Annotated[str, Field(pattern=r"^P[0-9]{3,9}$")]


class StatsQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    desde: AwareDatetime
    hasta: AwareDatetime
    equipo: Code | None = None
    resolucion: Literal["1m", "5m", "15m", "1h"] = "5m"

    @model_validator(mode="after")
    def valid_window(self):
        self.desde = self.desde.astimezone(timezone.utc)
        self.hasta = self.hasta.astimezone(timezone.utc)
        if not 0 < (self.hasta - self.desde).total_seconds() <= 86400:
            raise ValueError("La ventana debe ser positiva y no superar 24 horas")
        return self


class StatsPoint(BaseModel):
    tiempo: AwareDatetime
    equipo_codigo: str
    sede_id: str
    posesion_pct: float | None
    pases_completados_total: int | None
    tiros_intervalo: int | None
    recuperaciones_intervalo: int | None


class Statistics(BaseModel):
    partido_id: MatchID
    desde: AwareDatetime
    hasta: AwareDatetime
    resolucion: str
    items: list[StatsPoint]
    truncado: bool


class Envelope(BaseModel):
    data: Statistics

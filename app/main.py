import os
import threading
from contextlib import asynccontextmanager
from time import perf_counter
from typing import Annotated
from uuid import uuid4

import httpx
from fastapi import FastAPI, Query, Request, Response
from fastapi.responses import JSONResponse

from app.adapter import MeasuredAdapter
from app.models import Envelope, MatchID, StatsQuery

MODE = os.environ.get("HITO12_MODE", "baseline")
lock = threading.Lock()
totals = {"requests": 0, "errors": 0, "dependency_ms_sum": 0.0}


@asynccontextmanager
async def lifespan(app):
    app.state.adapter = MeasuredAdapter(os.environ.get("INFLUX_URL", "http://influxdb:8181"), MODE)
    yield
    app.state.adapter.close()


app = FastAPI(title="Fixture 2030 - Laboratorio Hito 12", lifespan=lifespan)


@app.middleware("http")
async def timing(request: Request, call_next):
    start = perf_counter()
    response = await call_next(request)
    response.headers["X-Hito12-Lab"] = "hito12-g09"
    response.headers["X-Request-ID"] = uuid4().hex
    response.headers["X-Api-Ms"] = f"{(perf_counter() - start) * 1000:.6f}"
    return response


@app.get("/health/live")
def live():
    return {"status": "ok", "lab": "hito12-g09"}


@app.get("/lab/identity")
def identity():
    return {"lab": "hito12-g09", "mode": MODE, "database": "hito12_g09",
            "upstream_commit": "772aeedf7e9f76a8eb17d18b35b21b34781f5a43"}


@app.get("/lab/metrics")
def metrics():
    with lock:
        return dict(totals)


@app.get("/api/v1/partidos/{partido_id}/estadisticas", response_model=Envelope)
def statistics(partido_id: MatchID, query: Annotated[StatsQuery, Query()],
               request: Request, response: Response):
    adapter = request.app.state.adapter
    failed = False
    try:
        rows = adapter.statistics(partido_id, query)
        response.headers["X-Dependency-Ms"] = f"{adapter.timing.dependency_ms:.6f}"
        return {"data": {"partido_id": partido_id, "desde": query.desde,
                         "hasta": query.hasta, "resolucion": query.resolucion,
                         "items": rows[:1000], "truncado": len(rows) > 1000}}
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        failed = True
        # No se reflejan SQL, URL interna, stack ni respuestas del motor.
        return JSONResponse(status_code=503, content={"error": "dependencia_no_disponible"})
    finally:
        with lock:
            totals["requests"] += 1
            totals["errors"] += int(failed)
            totals["dependency_ms_sum"] += getattr(adapter.timing, "dependency_ms", 0.0)

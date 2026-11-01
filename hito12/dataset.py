"""Datos sintéticos deterministas y oráculo independiente de SQL y de la API."""
import math
import random
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from hito12.common import DATABASE, GENERATED, ROOT, digest, read_json, write_json

RESOLUTIONS = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600}
MEASURES = ("posesion_pct", "pases_completados_total", "tiros_intervalo", "recuperaciones_intervalo")


def utc(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    # InfluxDB SQL puede serializar sus timestamps UTC sin sufijo de zona.
    # Nunca interpretarlos con la zona local de Windows.
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def iso(value):
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def config():
    cfg = read_json(ROOT / "config/dataset.json")
    if (cfg["database"] != DATABASE or cfg["measurement"] != "estadisticas_equipo" or
            not 4 <= cfg["matches"] <= 96 or not 1 <= cfg["minutes"] <= 120 or
            cfg["step_seconds"] not in (1, 5, 10, 30, 60)):
        raise ValueError("Dataset fuera de los límites del laboratorio")
    start = utc(cfg["start_utc"])
    if start.second or start.microsecond or start.minute % 5:
        raise ValueError("Usar un inicio UTC alineado a cinco minutos")
    return cfg


def match_ids(cfg):
    return [f"P{i:03d}" for i in range(1, cfg["matches"] + 1)]


def rows_for_match(cfg, index):
    rng = random.Random(cfg["seed"] + index)
    start = utc(cfg["start_utc"])
    totals = [0, 0]
    teams = ["AAA", "BBB"]  # códigos sintéticos; no representan selecciones reales
    for second in range(0, cfg["minutes"] * 60, cfg["step_seconds"]):
        possession = rng.randint(3500, 6500) / 100
        for side in range(2):
            totals[side] += rng.randint(0, 3)
            yield {"time": iso(start + timedelta(seconds=second)),
                   "partido_id": f"P{index:03d}", "equipo_codigo": teams[side],
                   "sede_id": f"S{(index - 1) % 6 + 1:02d}",
                   "posesion_pct": round(possession if side == 0 else 100 - possession, 2),
                   "pases_completados_total": totals[side],
                   "tiros_intervalo": int(rng.random() < 0.02),
                   "recuperaciones_intervalo": int(rng.random() < 0.08)}


def normalized_row(row, time_key="time", raw=False):
    keys = [time_key, "equipo_codigo", "sede_id", *MEASURES]
    if raw:
        keys.append("partido_id")
    result = {key: row[key] for key in keys}
    result[time_key] = iso(utc(result[time_key]))
    for key in MEASURES:
        number = result[key]
        if number is None or isinstance(number, bool) or not math.isfinite(float(number)):
            raise ValueError("Medida faltante o no finita")
        if key != "posesion_pct" and float(number) != int(number):
            raise ValueError("Contador no entero")
        result[key] = round(float(number), 6) if key == "posesion_pct" else int(number)
    return result


def canonical_rows(rows, time_key="time", raw=False):
    return sorted((normalized_row(row, time_key, raw) for row in rows),
                  key=lambda r: (r[time_key], r["equipo_codigo"], r["sede_id"]))


def aggregate(rows, resolution):
    buckets = defaultdict(list)
    width = RESOLUTIONS[resolution]
    for row in rows:
        epoch = int(utc(row["time"]).timestamp())
        buckets[(epoch // width * width, row["equipo_codigo"], row["sede_id"])].append(row)
    output = []
    for (epoch, team, stadium), group in sorted(buckets.items()):
        output.append({"tiempo": iso(datetime.fromtimestamp(epoch, timezone.utc)),
                       "equipo_codigo": team, "sede_id": stadium,
                       "posesion_pct": sum(r["posesion_pct"] for r in group) / len(group),
                       "pases_completados_total": max(r["pases_completados_total"] for r in group),
                       "tiros_intervalo": sum(r["tiros_intervalo"] for r in group),
                       "recuperaciones_intervalo": sum(r["recuperaciones_intervalo"] for r in group)})
    return canonical_rows(output, "tiempo")


def line_protocol(row):
    fields = ",".join(f"{key}={row[key]:.2f}" if key == "posesion_pct" else f"{key}={row[key]}i"
                      for key in MEASURES)
    tags = ",".join(f"{key}={row[key]}" for key in ("partido_id", "equipo_codigo", "sede_id"))
    return f"estadisticas_equipo,{tags} {fields} {int(utc(row['time']).timestamp())}\n"


def generate(cfg=None, directory=GENERATED):
    cfg = cfg or config()
    directory.mkdir(parents=True, exist_ok=True)
    oracle, hashes, counts = {}, {}, {}
    with (directory / "dataset.lp").open("w", encoding="utf-8", newline="\n") as out:
        for index, match in enumerate(match_ids(cfg), 1):
            rows = list(rows_for_match(cfg, index))
            out.writelines(line_protocol(row) for row in rows)
            hashes[match] = digest(canonical_rows(rows, raw=True))
            counts[match] = len(rows)
            for resolution in RESOLUTIONS:
                oracle[f"{match}/{resolution}"] = digest(aggregate(rows, resolution))
    manifest = {"config": cfg, "config_sha256": digest(cfg), "rows": sum(counts.values()),
                "counts": counts, "raw_sha256_by_match": hashes,
                "raw_sha256": digest(hashes), "oracle": oracle,
                "from": cfg["start_utc"],
                "to": iso(utc(cfg["start_utc"]) + timedelta(minutes=cfg["minutes"]))}
    write_json(directory / "manifest.json", manifest)
    return manifest


def validate_response(body, case, manifest):
    try:
        data = body["data"]
        if (data["partido_id"] != case["match"] or data["resolucion"] != case["resolution"] or
                data["truncado"] is not False or utc(data["desde"]) != utc(manifest["from"]) or
                utc(data["hasta"]) != utc(manifest["to"])):
            return False
        rows = canonical_rows(data["items"], "tiempo")
        return digest(rows) == manifest["oracle"][f"{case['match']}/{case['resolution']}"]
    except (KeyError, TypeError, ValueError, OverflowError):
        return False

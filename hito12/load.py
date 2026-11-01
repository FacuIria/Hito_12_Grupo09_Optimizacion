"""Generador de llegadas con tasa acotada, sin cola ilimitada ni reintentos."""
import csv
import math
import random
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import httpx
import psutil

from hito12.common import API, command, digest, now, write_json
from hito12.dataset import RESOLUTIONS, validate_response


def validate_config(cfg):
    ranges = {"concurrency": (1, 16), "rate_per_second": (0.1, 50),
              "warmup_seconds": (1, 60), "ramp_seconds": (1, 120),
              "steady_seconds": (5, 300), "timeout_seconds": (1, 10),
              "cooldown_seconds": (0, 60), "repetitions": (1, 5),
              "hot_matches": (1, 96), "hot_probability": (0, 1),
              "max_error_fraction": (0, 0.1), "error_min_samples": (1, 100),
              "min_available_memory_mb": (1024, 16384), "max_host_cpu_percent": (50, 95),
              "max_cpu_samples": (1, 5), "max_container_memory_percent": (50, 95),
              "monitor_interval_seconds": (1, 5), "min_disk_free_gb": (2, 100)}
    for key, (low, high) in ranges.items():
        value = cfg.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
            raise ValueError(f"{key} debe estar entre {low} y {high}")
    for key in ("concurrency", "repetitions", "hot_matches", "seed", "error_min_samples", "max_cpu_samples"):
        if not isinstance(cfg[key], int) or isinstance(cfg[key], bool):
            raise ValueError(f"{key} debe ser entero")
    if not cfg["resolutions"] or any(r not in RESOLUTIONS for r in cfg["resolutions"]):
        raise ValueError("Resoluciones inválidas")
    return cfg


def schedule(cfg, manifest):
    """El mismo plan exacto se reutiliza entre variantes y repeticiones."""
    validate_config(cfg)
    rng = random.Random(cfg["seed"])
    matches = list(manifest["counts"])
    hot = matches[:cfg["hot_matches"]]
    cold = matches[cfg["hot_matches"]:] or matches
    rate = cfg["rate_per_second"]
    warm, ramp, steady = (cfg[k] for k in ("warmup_seconds", "ramp_seconds", "steady_seconds"))
    times = [(i / rate, "warmup") for i in range(math.ceil(warm * rate)) if i / rate < warm]
    # Integral de una rampa lineal de 0 a rate: n = rate*t^2/(2*ramp).
    for i in range(1, math.ceil(rate * ramp / 2)):
        offset = math.sqrt(2 * ramp * i / rate)
        if offset < ramp:
            times.append((warm + offset, "ramp"))
    times.extend((warm + ramp + i / rate, "steady") for i in range(math.ceil(steady * rate))
                 if i / rate < steady)
    return [{"sequence": i, "offset_s": round(offset, 9), "phase": phase,
             "match": rng.choice(hot if rng.random() < cfg["hot_probability"] else cold),
             "resolution": rng.choice(cfg["resolutions"])}
            for i, (offset, phase) in enumerate(times)]


def percentile(values, q):
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    lower = math.floor(index)
    return ordered[lower] + (ordered[math.ceil(index)] - ordered[lower]) * (index - lower)


def distribution(values):
    return {"count": len(values), "min": min(values) if values else None,
            "mean": statistics.mean(values) if values else None,
            "p50": percentile(values, .5), "p90": percentile(values, .9),
            "p95": percentile(values, .95), "p99": percentile(values, .99),
            "max": max(values) if values else None}


def summarize(rows, cfg):
    selected = [r for r in rows if r["phase"] == "steady"]
    completed = [r for r in selected if r["kind"] not in {"capacity", "generator_late"}]
    successful = [r for r in completed if r["kind"] == "ok"]
    end = sum(cfg[k] for k in ("warmup_seconds", "ramp_seconds", "steady_seconds"))
    on_time = [r for r in successful if r["finished_s"] <= end]
    errors = len(completed) - len(successful)
    kinds = {kind: sum(r["kind"] == kind for r in selected) for kind in sorted({r["kind"] for r in selected})}
    return {"scheduled_observed": len(selected), "completed": len(completed), "successful": len(successful),
            "errors": errors, "errors_by_type": kinds,
            "error_fraction": errors / len(completed) if completed else None,
            "not_sent": len(selected) - len(completed),
            "successful_completed_within_window": len(on_time),
            "drained_successes": len(successful) - len(on_time),
            "throughput_success_per_second": len(on_time) / cfg["steady_seconds"],
            "latency_ms": distribution([r["latency_ms"] for r in completed]),
            "success_latency_ms": distribution([r["latency_ms"] for r in successful]),
            "api_ms": distribution([r["api_ms"] for r in completed if r["api_ms"] is not None]),
            "dependency_ms": distribution([r["dependency_ms"] for r in completed if r["dependency_ms"] is not None]),
            "validation_ms": distribution([r["validation_ms"] for r in completed]),
            "dispatch_lag_ms": distribution([r["dispatch_lag_ms"] for r in completed])}


def run_load(client, cfg, manifest, output, container_ids):
    """client es compartido y con pool también en la línea base; solo cambia API→motor."""
    plan = schedule(cfg, manifest)
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "plan.json", plan)
    rows, resources, reasons = [], [], []
    counters = {"sent": 0, "failed": 0}
    lock = threading.Lock()
    stop = threading.Event()
    monitor_done = threading.Event()
    slots = threading.BoundedSemaphore(cfg["concurrency"])
    start = time.perf_counter()
    started_utc = now()
    process = psutil.Process()
    process.cpu_percent()
    psutil.cpu_percent()

    def abort(reason):
        with lock:
            if reason not in reasons:
                reasons.append(reason)
        stop.set()

    def monitor():
        high_cpu = 0
        while not monitor_done.is_set():
            try:
                memory = psutil.virtual_memory()
                sample = {"elapsed_s": time.perf_counter() - start,
                          "host_cpu_percent": psutil.cpu_percent(),
                          "host_available_mb": memory.available / 2**20,
                          "generator_cpu_percent": process.cpu_percent(),
                          "generator_rss_mb": process.memory_info().rss / 2**20}
                import json
                raw = command(["docker", "stats", "--no-stream", "--format", "{{json .}}",
                               *container_ids.values()], timeout=8)
                stats = [json.loads(line) for line in raw.splitlines() if line.strip()]
                if len(stats) != len(container_ids):
                    raise RuntimeError("Muestreo incompleto")
                sample["containers"] = [{k: s.get(k) for k in
                    ("ID", "Name", "CPUPerc", "MemUsage", "MemPerc", "NetIO", "BlockIO", "PIDs")} for s in stats]
                with lock:
                    resources.append(sample)
                high_cpu = high_cpu + 1 if sample["host_cpu_percent"] >= cfg["max_host_cpu_percent"] else 0
                if high_cpu >= cfg["max_cpu_samples"]:
                    abort("CPU del host sostenida sobre el límite")
                if sample["host_available_mb"] < cfg["min_available_memory_mb"]:
                    abort("Memoria disponible del host insuficiente")
                if any(float(s["MemPerc"].strip("%")) >= cfg["max_container_memory_percent"] for s in stats):
                    abort("Memoria de contenedor sobre el límite")
            except Exception as exc:
                abort("Falló el monitor de recursos: " + type(exc).__name__)
                return
            monitor_done.wait(cfg["monitor_interval_seconds"])

    def request(case):
        begin = time.perf_counter()
        result = dict(case, kind="network", http_status=0, latency_ms=0.0, api_ms=None,
                      dependency_ms=None, validation_ms=0.0, server_request_id="",
                      dispatch_lag_ms=(begin - start - case["offset_s"]) * 1000)
        try:
            response = client.get(API + f"/api/v1/partidos/{case['match']}/estadisticas",
                params={"desde": manifest["from"], "hasta": manifest["to"], "resolucion": case["resolution"]},
                timeout=cfg["timeout_seconds"])
            result["latency_ms"] = (time.perf_counter() - begin) * 1000
            result["finished_s"] = time.perf_counter() - start
            result["http_status"] = response.status_code
            result["server_request_id"] = response.headers.get("X-Request-ID", "")
            for header, key in (("X-Api-Ms", "api_ms"), ("X-Dependency-Ms", "dependency_ms")):
                if response.headers.get(header):
                    result[key] = float(response.headers[header])
            if response.status_code != 200:
                result["kind"] = f"http_{response.status_code}"
            else:
                check_start = time.perf_counter()
                valid = response.headers.get("X-Hito12-Lab") == "hito12-g09" and validate_response(response.json(), case, manifest)
                result["validation_ms"] = (time.perf_counter() - check_start) * 1000
                result["kind"] = "ok" if valid else "integrity"
        except httpx.TimeoutException:
            result["kind"] = "timeout"
        except httpx.RequestError:
            result["kind"] = "network"
        except (ValueError, KeyError, TypeError):
            result["kind"] = "integrity"
        except Exception:
            result["kind"] = "generator_error"
            abort("Error interno del generador")
        finally:
            if "finished_s" not in result:
                result["latency_ms"] = (time.perf_counter() - begin) * 1000
                result["finished_s"] = time.perf_counter() - start
            with lock:
                rows.append(result)
                counters["sent"] += 1
                counters["failed"] += int(result["kind"] != "ok")
                count, failed = counters["sent"], counters["failed"]
            if result["kind"] == "integrity":
                abort("Respuesta distinta del oráculo independiente")
            if count >= cfg["error_min_samples"] and failed / count > cfg["max_error_fraction"]:
                abort("Tasa de errores superior al límite")
            slots.release()

    worker = threading.Thread(target=monitor, daemon=True)
    worker.start()
    try:
        with ThreadPoolExecutor(max_workers=cfg["concurrency"]) as executor:
            for case in plan:
                if stop.wait(max(0, start + case["offset_s"] - time.perf_counter())):
                    break
                lag = time.perf_counter() - start - case["offset_s"]
                # No recuperar una agenda atrasada con una ráfaga artificial.
                late = lag > max(0.2, 1 / cfg["rate_per_second"])
                if late or not slots.acquire(blocking=False):
                    with lock:
                        rows.append(dict(case, kind="generator_late" if late else "capacity", http_status=0,
                                         latency_ms=None, api_ms=None, dependency_ms=None, validation_ms=0,
                                         server_request_id="", dispatch_lag_ms=lag * 1000,
                                         finished_s=time.perf_counter() - start))
                    continue
                executor.submit(request, case)
            total = sum(cfg[k] for k in ("warmup_seconds", "ramp_seconds", "steady_seconds"))
            stop.wait(max(0, start + total - time.perf_counter()))
    except KeyboardInterrupt:
        abort("Interrumpido por el operador")
    finally:
        monitor_done.set()
        worker.join(timeout=10)
    rows.sort(key=lambda r: r["sequence"])
    if rows:
        with (output / "requests.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    summary = {"started_utc": started_utc, "finished_utc": now(), "aborted": bool(reasons),
               "abort_reasons": reasons, "planned_operations": len(plan), "observed_operations": len(rows),
               "wall_seconds_including_drain": time.perf_counter() - start,
               "schedule_sha256": digest(plan), "steady": summarize(rows, cfg),
               "all_phases": {"sent": sum(r["kind"] not in {"capacity", "generator_late"} for r in rows),
                              "ok": sum(r["kind"] == "ok" for r in rows),
                              "integrity_errors": sum(r["kind"] == "integrity" for r in rows)}}
    write_json(output / "resources.json", resources)
    write_json(output / "load.json", summary)
    return summary

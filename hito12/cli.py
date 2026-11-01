"""Entrada única: python -m hito12.cli --help. No admite destinos arbitrarios."""
import argparse
import json
import shutil
import socket
import sys
import time
from pathlib import Path

import httpx
import psutil

from hito12.common import (API, EVIDENCE, GENERATED, INFLUX, ROOT, RUNTIME, command,
    compose, containers, digest, file_hash, identity, local_docker, metadata, now, read_json,
    source_fingerprint, sql, write_json)
from hito12.dataset import config, generate, validate_response
from hito12.integrity import validate_source
from hito12.load import run_load, validate_config
from hito12.profiles import DAEMON_MIN_BYTES, LOAD_CONFIG, PROFILE, START_FREE_MB


def client():
    return httpx.Client(timeout=10, trust_env=False,
                        limits=httpx.Limits(max_connections=16, max_keepalive_connections=16))


def resources(cfg, starting=False):
    memory = psutil.virtual_memory()
    minimum = max(cfg["min_available_memory_mb"], START_FREE_MB if starting else 0)
    if memory.available / 2**20 < minimum:
        raise RuntimeError(f"Se requieren {minimum} MiB libres; cerrar aplicaciones y volver a intentar.")
    if shutil.disk_usage(ROOT).free / 2**30 < cfg["min_disk_free_gb"]:
        raise RuntimeError("Espacio de disco insuficiente")
    info = local_docker()
    if info["MemTotal"] < DAEMON_MIN_BYTES:
        raise RuntimeError(f"RAM del daemon insuficiente para el perfil {PROFILE}.")
    return info


def await_api(expected):
    with client() as http:
        for _ in range(60):
            try:
                identity(http, expected)
                response = http.get(INFLUX + "/health", timeout=5)
                response.raise_for_status()
                return
            except (httpx.HTTPError, ValueError, RuntimeError):
                time.sleep(1)
    raise RuntimeError("La API no inició. Revisar docker compose -p hito12-g09 logs api.")


def up(args):
    cfg = validate_config(read_json(ROOT / LOAD_CONFIG))
    info = resources(cfg, starting=True)
    # No ocupar puertos de otros procesos. Si ya hay laboratorio, validar su identidad.
    ids = compose("ps", "--all", "--quiet").splitlines()
    if ids:
        raise RuntimeError("El laboratorio ya existe. Usar reanudar o detener; no se reconstruye implícitamente.")
    for port in (8012, 18182):
        with socket.socket() as sock:
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                raise RuntimeError(f"Puerto {port} ocupado. No se detendrá el proceso que lo utiliza.") from None
    print("Construyendo y levantando únicamente el proyecto hito12-g09...", flush=True)
    compose("build", "api", mode="baseline", timeout=900)
    resources(cfg, starting=True)
    compose("pull", "influxdb", timeout=600)
    resources(cfg, starting=True)
    compose("up", "-d", "--no-build", mode="baseline", timeout=900)
    try:
        resources(cfg)
    except RuntimeError:
        compose("stop", "api", "influxdb")
        raise
    await_api("baseline")
    own = containers()
    write_json(RUNTIME / "environment.json", {"date_utc": now(), "docker": info, "containers": own})
    print("Entorno iniciado. Próximo paso: preparar_datos.ps1")


def resume(args):
    resources(validate_config(read_json(ROOT / LOAD_CONFIG)), starting=True)
    containers(require_running=False)
    # start nunca crea ni reconstruye contenedores; ámbito fijado por compose.
    compose("start", timeout=90)
    with client() as http:
        for _ in range(60):
            try:
                identity(http)
                containers()
                print("Laboratorio reanudado; se conserva su modo anterior.")
                return
            except (httpx.HTTPError, RuntimeError):
                time.sleep(1)
    raise RuntimeError("No se pudo reanudar el laboratorio")


def load_manifest():
    manifest = read_json(GENERATED / "manifest.json")
    if manifest["config_sha256"] != digest(config()):
        raise RuntimeError("Cambió config/dataset.json. No mezclar datasets en un volumen existente.")
    # Regenerar el oráculo en memoria/archivos propios asegura que no provenga de la API.
    expected = generate(config())
    if manifest != expected:
        raise RuntimeError("El manifiesto no coincide con el generador actual.")
    return manifest


def prepare(args):
    resources(validate_config(read_json(ROOT / LOAD_CONFIG)))
    observed = metadata()
    own = containers()
    cfg = config()
    state_path = RUNTIME / "dataset-lock.json"
    if state_path.exists() and read_json(state_path)["dataset_sha256"] != digest(cfg):
        raise RuntimeError("El volumen ya pertenece a otro dataset. No se sobrescribe.")
    manifest = generate(cfg)
    with client() as http:
        identity(http)
        # Un volumen con datos sin estado de preparación local requiere inspección manual.
        # Nunca reinterpretar un fallo de red/autenticación como base vacía.
        try:
            existing = sql(http, "SELECT COUNT(*) AS total FROM estadisticas_equipo")
        except httpx.HTTPStatusError as exc:
            message = exc.response.text.lower()
            missing = (exc.response.status_code in (400, 404, 500) and
                       any(term in message for term in ("not found", "does not exist", "doesn't exist")) and
                       any(term in message for term in ("database", "estadisticas_equipo")))
            if not missing:
                raise
            existing = [{"total": 0}]
        if int(existing[0]["total"]) and not state_path.exists():
            raise RuntimeError("Hay datos sin manifiesto local: no se escribirá sobre ellos.")
        write_json(state_path, {"dataset_sha256": digest(cfg), "influx_container": own["influxdb"]["id"]})
        report = {"date_utc": now(), "metadata": observed, "dataset": manifest, "attempted_records": 0,
                  "acknowledged_records": 0, "failed_batch_records": 0,
                  "batch_size": 1000, "existing_records": int(existing[0]["total"]),
                  "write_semantics": "Upsert idempotente por tabla, tags y timestamp; sin reintentos automáticos",
                  "completed": False}
        run = new_directory("preparacion")
        batch = []
        try:
            with (GENERATED / "dataset.lp").open(encoding="utf-8") as stream:
                for line in stream:
                    batch.append(line)
                    if len(batch) == 1000:
                        resources(validate_config(read_json(ROOT / LOAD_CONFIG)))
                        write_batch(http, batch, report)
                        batch = []
                if batch:
                    resources(validate_config(read_json(ROOT / LOAD_CONFIG)))
                    write_batch(http, batch, report)
            integrity = validate_source(http, manifest)
            report["integrity"] = integrity
            report["completed"] = integrity["passed"]
        except BaseException as exc:
            report["failure_type"] = type(exc).__name__
            raise
        finally:
            report["finished_utc"] = now()
            write_json(run / "preparation.json", report)
        if not report["completed"]:
            raise RuntimeError("La preparación no pasó integridad; no ejecutar la carga.")
    print(f"Dataset listo: {manifest['rows']} registros. Evidencia: {run.relative_to(ROOT)}")


def write_batch(http, batch, report):
    report["attempted_records"] += len(batch)
    try:
        response = http.post(INFLUX + "/api/v3/write_lp",
            params={"db": "hito12_g09", "precision": "second", "accept_partial": "false", "no_sync": "false"},
            content="".join(batch).encode(), headers={"Content-Type": "text/plain"}, timeout=30)
        response.raise_for_status()
        report["acknowledged_records"] += len(batch)
    except httpx.HTTPError:
        report["failed_batch_records"] += len(batch)
        # Una escritura con timeout puede haber sido aplicada: no llamarla rechazada.
        report["failure_note"] = "Lote sin confirmación; aceptación desconocida hasta validar la fuente."
        raise


def new_directory(prefix):
    from datetime import datetime, timezone
    path = EVIDENCE / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ_") + prefix)
    path.mkdir(parents=True, exist_ok=False)
    return path


def resolve_baseline(value):
    if value:
        path = Path(value)
        path = path if path.is_absolute() else ROOT / path
    else:
        path = ROOT / read_json(RUNTIME / "last_baseline.json")["path"]
    if path.is_dir():
        path = path / "experiment.json"
    data = read_json(path)
    if data["mode"] != "baseline" or not data.get("completed") or not data.get("trials"):
        raise RuntimeError("Se requiere una línea base completa y válida.")
    return path, data


def benchmark(args):
    cfg_path = ROOT / args.config
    cfg = validate_config(read_json(cfg_path))
    if args.mode == "pooled":
        if Path(args.config).name in {"humo.json", "humo_compacto.json"}:
            raise RuntimeError("El escenario de humo no acredita la comparación final.")
    resources(cfg)
    manifest = load_manifest()
    before = metadata()
    mode = args.mode
    baseline = None
    if mode == "pooled":
        baseline_path, baseline = resolve_baseline(args.baseline)
        if not args.hypothesis or len(args.hypothesis.strip()) < 30 or not args.evidence:
            raise RuntimeError("Registrar --hypothesis (al menos 30 caracteres) y --evidence de la línea base.")
        evidence_path = (ROOT / args.evidence).resolve()
        if not evidence_path.is_relative_to(baseline_path.parent.resolve()) or not evidence_path.is_file():
            raise RuntimeError("--evidence debe identificar un archivo real dentro de la línea base elegida.")
        if (baseline["config"] != cfg or baseline["dataset_sha256"] != manifest["raw_sha256"] or
                baseline["metadata"]["source_sha256"] != before["source_sha256"]):
            raise RuntimeError("Cambió el código, escenario o dataset desde la línea base; medir otra línea base.")
        if (baseline["metadata"]["containers"]["influxdb"]["id"] != before["containers"]["influxdb"]["id"] or
                baseline["metadata"]["containers"]["api"]["image_id"] != before["containers"]["api"]["image_id"]):
            raise RuntimeError("Cambió el motor o la imagen API; medir otra línea base.")
        # Rechazar condiciones incompatibles antes de cambiar modo o emitir carga.
        from hito12.compare import compatibility
        candidate = dict(baseline, mode="pooled", metadata=before)
        issues = compatibility(baseline, candidate)
        if issues:
            raise RuntimeError("Preflight de comparación rechazado: " + "; ".join(issues))
    experiment = new_directory(mode)
    report = {"schema_version": 1, "mode": mode, "completed": False, "config": cfg,
              "config_sha256": digest(cfg), "dataset_sha256": manifest["raw_sha256"],
              "dataset_config": manifest["config"], "dataset_records": manifest["rows"],
              "metadata": before, "trials": []}
    if baseline:
        report["baseline_path"] = str(baseline_path.relative_to(ROOT)).replace("\\", "/")
        report["hypothesis"] = {"recorded_utc": now(), "statement": args.hypothesis,
                                "baseline_evidence": str(evidence_path.relative_to(ROOT)).replace("\\", "/"),
                                "evidence_sha256": file_hash(evidence_path),
                                "change": "Cliente httpx persistente con pool máximo de 16 conexiones"}
        write_json(experiment / "hypothesis.json", report["hypothesis"])
    write_json(experiment / "experiment.json", report)
    # Mismo tag e ID de imagen; solo cambia una variable en el servicio API propio.
    compose("up", "-d", "--no-deps", "--no-build", "api", mode=mode, timeout=120)
    await_api(mode)
    with client() as http:
        identity(http, mode)
        report["metadata"] = metadata()
        try:
            for index in range(1, cfg["repetitions"] + 1):
                print(f"{mode}: repetición {index}/{cfg['repetitions']}", flush=True)
                trial_dir = experiment / f"trial_{index:02d}"
                trial_dir.mkdir()
                trial = {"number": index, "completed": False}
                report["trials"].append(trial)
                resources(cfg)
                own = containers()
                pre = validate_source(http, manifest)
                write_json(trial_dir / "integrity_before.json", pre)
                trial["integrity_before"] = pre["passed"]
                if not pre["passed"]:
                    raise RuntimeError("Integridad previa inválida")
                metrics_before = http.get(API + "/lab/metrics").json()
                result = run_load(http, cfg, manifest, trial_dir, {k: v["id"] for k, v in own.items()})
                trial["load"] = result
                metrics_after = http.get(API + "/lab/metrics").json()
                write_json(trial_dir / "api_metrics.json", {"before": metrics_before, "after": metrics_after})
                post = validate_source(http, manifest)
                write_json(trial_dir / "integrity_after.json", post)
                trial["integrity_after"] = post["passed"] and pre["raw_sha256"] == post["raw_sha256"]
                after_containers = containers()
                stable = all(own[k]["id"] == after_containers[k]["id"] and
                             own[k]["restart_count"] == after_containers[k]["restart_count"] for k in own)
                trial["containers_stable"] = stable
                trial["completed"] = not result["aborted"] and trial["integrity_after"] and stable
                write_json(experiment / "experiment.json", report)
                if not trial["completed"]:
                    raise RuntimeError("Prueba interrumpida, reinicio o integridad inválida. Revisar evidencia.")
                if index < cfg["repetitions"]:
                    time.sleep(cfg["cooldown_seconds"])
            if source_fingerprint() != report["metadata"]["source_sha256"]:
                raise RuntimeError("El código cambió durante la prueba")
            report["completed"] = True
        except BaseException as exc:
            report["failure_type"] = type(exc).__name__
            raise
        finally:
            report["finished_utc"] = now()
            write_json(experiment / "experiment.json", report)
    pointer = {"path": str(experiment.relative_to(ROOT)).replace("\\", "/")}
    write_json(RUNTIME / f"last_{mode}.json", pointer)
    print(f"Evidencia guardada: {pointer['path']}")
    if mode == "baseline":
        print("Revisar trial_*/load.json y resources.json; luego registrar la hipótesis para la candidata.")
    else:
        from hito12.compare import compare
        compare(baseline_path, experiment / "experiment.json")


def check_integrity(args):
    local_docker()
    containers()
    manifest = load_manifest()
    with client() as http:
        identity(http)
        result = validate_source(http, manifest)
    path = new_directory("integridad") / "integrity.json"
    write_json(path, result)
    if not result["passed"]:
        raise RuntimeError("Integridad inválida")
    print(f"Integridad verificada: {result['actual_records']} registros. {path.relative_to(ROOT)}")


def stop(args):
    local_docker()
    containers(require_running=False)
    # stop no borra contenedores, redes ni datos; proyecto y servicios explícitos.
    compose("stop", "api", "influxdb", timeout=60)
    print("Solo se detuvo Hito 12. Volumen, resultados y Hito 11 se conservan.")


def doctor(args):
    report = {"date_utc": now(), "profile": PROFILE, "python": sys.version.split()[0],
              "cpu_logical": psutil.cpu_count(), "ram_total_gib": round(psutil.virtual_memory().total / 2**30, 2),
              "ram_available_gib": round(psutil.virtual_memory().available / 2**30, 2),
              "disk_free_gib": round(shutil.disk_usage(ROOT).free / 2**30, 2)}
    try:
        report["docker"] = local_docker()
        report["compose_version"] = command(["docker", "compose", "version", "--short"])
    except (RuntimeError, FileNotFoundError, OSError) as exc:
        report["docker"] = {"available": False, "reason": str(exc)[:400]}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    write_json(RUNTIME / "preflight.json", report)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    for name, func in (("doctor", doctor), ("up", up), ("resume", resume), ("prepare", prepare),
                       ("integrity", check_integrity), ("stop", stop)):
        sub.add_parser(name).set_defaults(func=func)
    gen = sub.add_parser("generate")
    gen.set_defaults(func=lambda _: print(f"Generados {generate()['rows']} registros; no se escribieron en InfluxDB."))
    run = sub.add_parser("run")
    run.add_argument("--mode", choices=["baseline", "pooled"], required=True)
    run.add_argument("--config", default=LOAD_CONFIG)
    run.add_argument("--baseline")
    run.add_argument("--hypothesis")
    run.add_argument("--evidence")
    run.set_defaults(func=benchmark)
    comp = sub.add_parser("compare")
    comp.add_argument("baseline")
    comp.add_argument("optimized")
    def compare_args(a):
        from hito12.compare import compare
        compare(Path(a.baseline), Path(a.optimized))
    comp.set_defaults(func=compare_args)
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("Interrumpido. No se eliminaron datos.", file=sys.stderr)
        return 130
    except Exception as exc:
        # No guardar tracebacks de red ni contenido recibido del servidor.
        message = str(exc) if not isinstance(exc, httpx.HTTPError) else type(exc).__name__ + ": revisar disponibilidad local de Hito 12"
        print(f"ERROR: {message}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Comparación de experimentos reales. Rechaza condiciones incompatibles."""
import csv
import statistics
from pathlib import Path

from hito12.common import read_json, write_json


def compatibility(base, optimized):
    issues = []
    if base.get("mode") != "baseline" or optimized.get("mode") != "pooled":
        issues.append("Se requieren baseline y pooled, en ese orden")
    for label, value in (("baseline", base), ("pooled", optimized)):
        if not value.get("completed") or not value.get("trials"):
            issues.append(label + ": experimento incompleto")
        for trial in value.get("trials", []):
            if not all(trial.get(k) for k in ("completed", "integrity_before", "integrity_after", "containers_stable")):
                issues.append(label + ": integridad o ejecución inválida")
    for key in ("config", "dataset_sha256", "dataset_config", "dataset_records"):
        if base.get(key) != optimized.get(key):
            issues.append("Diferencia de " + key)
    for key in ("profile", "source_sha256", "machine_id_sha256", "platform", "python", "logical_cpus", "memory_total_bytes", "docker", "versions"):
        if base["metadata"].get(key) != optimized["metadata"].get(key):
            issues.append("Entorno distinto: " + key)
    for service in ("api", "influxdb"):
        for key in ("image_id", "memory_limit", "nano_cpus"):
            if base["metadata"]["containers"][service][key] != optimized["metadata"]["containers"][service][key]:
                issues.append(f"Distinto {service}.{key}")
    if base["metadata"]["containers"]["influxdb"]["id"] != optimized["metadata"]["containers"]["influxdb"]["id"]:
        issues.append("Se recreó el motor entre variantes")
    if len(base.get("trials", [])) != len(optimized.get("trials", [])):
        issues.append("Distinta cantidad de repeticiones")
    schedules = {t["load"]["schedule_sha256"] for e in (base, optimized)
                 for t in e.get("trials", []) if "load" in t}
    if len(schedules) != 1:
        issues.append("Planes de solicitudes diferentes")
    return issues


def get_nested(data, keys):
    for key in keys.split("."):
        data = data[key]
    return data


def compare(baseline_path, optimized_path):
    baseline_path, optimized_path = Path(baseline_path), Path(optimized_path)
    if baseline_path.is_dir():
        baseline_path /= "experiment.json"
    if optimized_path.is_dir():
        optimized_path /= "experiment.json"
    base, optimized = read_json(baseline_path), read_json(optimized_path)
    issues = compatibility(base, optimized)
    if issues:
        raise ValueError("Comparación rechazada: " + "; ".join(issues))
    fields = [
        ("Latencia p50", "latency_ms.p50", "ms"),
        ("Latencia p90", "latency_ms.p90", "ms"),
        ("Latencia p95", "latency_ms.p95", "ms"),
        ("Latencia p99", "latency_ms.p99", "ms"),
        ("Latencia media", "latency_ms.mean", "ms"),
        ("Latencia exitosa p95", "success_latency_ms.p95", "ms"),
        ("Latencia exitosa p99", "success_latency_ms.p99", "ms"),
        ("API p95", "api_ms.p95", "ms"),
        ("Llamada al motor p95", "dependency_ms.p95", "ms"),
        ("Throughput exitoso", "throughput_success_per_second", "op/s"),
        ("Operaciones completadas", "completed", "operaciones"),
        ("Operaciones exitosas", "successful", "operaciones"),
        ("Errores", "errors", "operaciones"),
        ("Fracción de errores", "error_fraction", "fracción"),
        ("No enviadas", "not_sent", "operaciones"),
        ("Atraso de despacho p95", "dispatch_lag_ms.p95", "ms"),
        ("Validación del cliente p95", "validation_ms.p95", "ms"),
    ]
    rows = []
    for label, key, unit in fields:
        values = [[get_nested(t["load"]["steady"], key) for t in e["trials"]] for e in (base, optimized)]
        if any(v is None for series in values for v in series):
            raise ValueError(f"Sin muestras suficientes para {label}; no generar una mejora ficticia")
        before, after = [statistics.median(v) for v in values]
        rows.append({"metric": label, "unit": unit, "baseline_median": before,
                     "baseline_min": min(values[0]), "baseline_max": max(values[0]),
                     "pooled_median": after, "pooled_min": min(values[1]), "pooled_max": max(values[1]),
                     "change_percent": (after - before) / before * 100 if before else None})
    warnings = []
    if any(t["load"]["steady"]["not_sent"] for e in (base, optimized) for t in e["trials"]):
        warnings.append("Hubo llegadas no enviadas: revisar capacidad del generador y concurrencia antes de atribuir una mejora.")
    if any(t["load"]["steady"]["errors"] for e in (base, optimized) for t in e["trials"]):
        warnings.append("Hubo errores: comparar tipos y latencias exitosas; una respuesta de error rápida puede reducir percentiles.")
    if len(base["trials"]) < 3:
        warnings.append("Menos de tres repeticiones: resultado exploratorio; repetir el escenario final.")
    if any(t["load"]["steady"]["successful"] < 1000 for e in (base, optimized) for t in e["trials"]):
        warnings.append("Menos de 1000 respuestas exitosas en alguna repetición: el 1% superior contiene menos de 10 observaciones; interpretar p99 con cautela. Este umbral es orientativo, no una garantía estadística.")
    warnings.append("Tasa de llegada acotada: el throughput observado no demuestra capacidad máxima.")
    warnings.append("Orden baseline→pooled; cachés del motor, carga externa y deriva térmica pueden influir.")
    output = optimized_path.parent
    with (output / "comparison.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    resource_rows = []
    for label, path, experiment in (("baseline", baseline_path, base), ("pooled", optimized_path, optimized)):
        for trial in experiment["trials"]:
            samples = read_json(path.parent / f"trial_{trial['number']:02d}" / "resources.json")
            if not samples:
                raise ValueError("No hay evidencia de recursos")
            record = {"mode": label, "trial": trial["number"], "samples": len(samples),
                      "host_cpu_max_percent": max(s["host_cpu_percent"] for s in samples),
                      "host_memory_min_available_mb": min(s["host_available_mb"] for s in samples),
                      "generator_cpu_max_percent": max(s["generator_cpu_percent"] for s in samples),
                      "generator_rss_max_mb": max(s["generator_rss_mb"] for s in samples)}
            for service in ("api", "influxdb"):
                observed = [c for s in samples for c in s["containers"] if service in c["Name"]]
                record[service + "_cpu_max_percent"] = max(float(c["CPUPerc"].strip("%")) for c in observed)
                record[service + "_memory_max_percent"] = max(float(c["MemPerc"].strip("%")) for c in observed)
            resource_rows.append(record)
    write_json(output / "comparison.json", {"comparable": True, "metrics": rows,
               "resources": resource_rows, "warnings": warnings,
               "interpretation": "Cambios medidos; una variación porcentual no implica significación estadística."})
    lines = ["# Comparación real antes/después", "",
             f"Línea base: `{baseline_path.parent.name}`. Candidata: `{optimized_path.parent.name}`.", "",
             "Mediana de las métricas de cada repetición durante sostenimiento; rango mínimo–máximo entre repeticiones.",
             "Los percentiles no se promedian ni se presentan como un percentil conjunto.", "",
             "| Métrica | Unidad | Baseline mediana [rango] | Pool mediana [rango] | Cambio % |",
             "|---|---|---:|---:|---:|"]
    for r in rows:
        delta = "n/a (base cero)" if r["change_percent"] is None else f"{r['change_percent']:+.2f}"
        lines.append(f"| {r['metric']} | {r['unit']} | {r['baseline_median']:.3f} "
                     f"[{r['baseline_min']:.3f}, {r['baseline_max']:.3f}] | {r['pooled_median']:.3f} "
                     f"[{r['pooled_min']:.3f}, {r['pooled_max']:.3f}] | {delta} |")
    lines += ["", "El signo negativo reduce la métrica; es favorable para latencia/errores y desfavorable para throughput.",
              "", "## Recursos", "", "Máximos observados en muestras discretas (todas las fases, no picos garantizados).", "",
              "| Variante | Repetición | CPU host % | CPU API % | CPU motor % | RAM API % límite | RAM motor % límite | RAM generador MiB |",
              "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for r in resource_rows:
        lines.append(f"| {r['mode']} | {r['trial']} | {r['host_cpu_max_percent']:.1f} | "
                     f"{r['api_cpu_max_percent']:.1f} | {r['influxdb_cpu_max_percent']:.1f} | "
                     f"{r['api_memory_max_percent']:.1f} | {r['influxdb_memory_max_percent']:.1f} | "
                     f"{r['generator_rss_max_mb']:.1f} |")
    lines += ["", "## Límites de interpretación", "", *["- " + w for w in warnings], "",
              "## Decisión del equipo", "", "Pendiente: interpretar cambios, regresiones, errores, recursos y trade-offs; "
              "aceptar o rechazar el pool con referencia a estas mediciones.", ""]
    (output / "comparison.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Comparación generada: {output / 'comparison.md'}")
    return rows

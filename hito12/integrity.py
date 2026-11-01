"""Comprobación completa del dataset; un HTTP 200 no acredita integridad."""
from hito12.common import digest, now, sql
from hito12.dataset import canonical_rows


def validate_source(client, manifest):
    count = int(sql(client, "SELECT COUNT(*) AS total FROM estadisticas_equipo")[0]["total"])
    hashes, counts, duplicates = {}, {}, 0
    for match in manifest["counts"]:
        # IDs generados localmente y validados por el manifiesto; no entrada de usuario.
        if not match.startswith("P") or not match[1:].isdigit():
            raise ValueError("ID de partido inválido")
        rows = sql(client, f"SELECT time, partido_id, equipo_codigo, sede_id, posesion_pct, "
                   f"pases_completados_total, tiros_intervalo, recuperaciones_intervalo "
                   f"FROM estadisticas_equipo WHERE partido_id = '{match}' "
                   "ORDER BY time, equipo_codigo, sede_id")
        normalized = canonical_rows(rows, raw=True)
        keys = [(r["time"], r["partido_id"], r["equipo_codigo"], r["sede_id"]) for r in normalized]
        duplicates += len(keys) - len(set(keys))
        counts[match] = len(rows)
        hashes[match] = digest(normalized)
    passed = (count == manifest["rows"] and counts == manifest["counts"] and
              hashes == manifest["raw_sha256_by_match"] and duplicates == 0)
    return {"date_utc": now(), "passed": passed, "expected_records": manifest["rows"],
            "actual_records": count, "counts": counts, "duplicates": duplicates,
            "raw_sha256_by_match": hashes, "raw_sha256": digest(hashes),
            "method": "Lectura completa; clave única y SHA256 de todos los campos normalizados"}

"""Perfiles cerrados: un laboratorio compacto no acredita capacidad del estándar."""
import os

PROFILE = os.environ.get("HITO12_PROFILE", "estandar")
if PROFILE not in {"estandar", "compacto"}:
    raise RuntimeError("HITO12_PROFILE debe ser estandar o compacto")
COMPACT = PROFILE == "compacto"
COMPOSE_FILE = "compose.compacto.yaml" if COMPACT else "compose.yaml"
LOAD_CONFIG = "config/carga_compacto.json" if COMPACT else "config/carga.json"
DATASET_CONFIG = "config/dataset_compacto.json" if COMPACT else "config/dataset.json"
START_FREE_MB = 1536 if COMPACT else 4096
DAEMON_MIN_BYTES = (2 if COMPACT else 4) * 2**30
LIMITS = {"api": (192 * 2**20, 500_000_000), "influxdb": (768 * 2**20, 10**9)} if COMPACT else {
    "api": (512 * 2**20, 10**9), "influxdb": (2 * 2**30, 2 * 10**9)}
VOLUME = "hito12-g09_datos_hito12" + ("_compacto" if COMPACT else "")

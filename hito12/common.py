"""Rutas fijas, hashes y acceso restringido al laboratorio local."""
import hashlib
import json
import os
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".runtime"
GENERATED = ROOT / "datos" / "generados"
EVIDENCE = ROOT / "docs" / "evidencia"
API = "http://127.0.0.1:8012"
INFLUX = "http://127.0.0.1:18182"
DATABASE = "hito12_g09"
PROJECT = "hito12-g09"
SOURCE_PATHS = ["app", "hito12", "scripts", "config", "tests", "Dockerfile",
                "compose.yaml", "requirements.txt", "requirements-dev.txt",
                "requirements-lock.txt", "requirements-dev-lock.txt", ".dockerignore"]


def now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_fingerprint():
    files = []
    for name in SOURCE_PATHS:
        path = ROOT / name
        files.extend(path.rglob("*")) if path.is_dir() else files.append(path)
    return digest({str(p.relative_to(ROOT)).replace("\\", "/"):
                   hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
                   for p in sorted(files) if p.is_file() and "__pycache__" not in p.parts
                   and p.suffix not in {".pyc", ".pyo"}})


def command(args, *, timeout=30, env=None):
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=timeout, env=env)
    if result.returncode:
        # Comandos construidos aquí no incluyen credenciales. No guardar stderr de Docker en evidencias.
        raise RuntimeError(f"Falló {args[0]} {args[1]}: {result.stderr.strip()[:1200]}")
    return result.stdout.strip()


def compose(*args, mode="baseline", timeout=60):
    env = dict(os.environ)
    env["HITO12_MODE"] = mode
    return command(["docker", "compose", "--project-name", PROJECT,
                    "--file", str(ROOT / "compose.yaml"), *args], timeout=timeout, env=env)


def local_docker():
    if os.environ.get("DOCKER_HOST") or os.environ.get("DOCKER_CONTEXT"):
        raise RuntimeError("Usar el contexto local de Docker Desktop sin DOCKER_HOST/DOCKER_CONTEXT.")
    context = command(["docker", "context", "show"])
    config = json.loads(command(["docker", "context", "inspect", context]))[0]
    endpoint = config["Endpoints"]["docker"]["Host"]
    if not endpoint.startswith(("npipe://", "unix://")):
        raise RuntimeError("Se requiere un daemon Docker local, no remoto.")
    info = json.loads(command(["docker", "info", "--format", "{{json .}}"], timeout=30))
    if info["OSType"] != "linux":
        raise RuntimeError("Docker Desktop debe usar contenedores Linux.")
    return {k: info.get(k) for k in ("ServerVersion", "OSType", "Architecture", "NCPU", "MemTotal")}


def containers():
    """Solo IDs del proyecto propio; no inspeccionar ni operar otros contenedores."""
    ids = compose("ps", "--all", "--quiet").splitlines()
    if not ids:
        raise RuntimeError("No existe el laboratorio Hito 12; ejecutar iniciar_entorno.ps1.")
    result = {}
    for cid in ids:
        item = json.loads(command(["docker", "inspect", cid]))[0]
        labels = item["Config"].get("Labels", {})
        service = labels.get("com.docker.compose.service")
        if (labels.get("com.docker.compose.project") != PROJECT or
                labels.get("edu.fixture.hito") != "12" or service not in {"api", "influxdb"}):
            raise RuntimeError("Recurso sin identidad de laboratorio Hito 12.")
        if not item["State"]["Running"] or item["State"].get("OOMKilled"):
            raise RuntimeError(f"Servicio {service} detenido o sin memoria.")
        networks = item["NetworkSettings"]["Networks"]
        if set(networks) != {PROJECT + "_laboratorio"}:
            raise RuntimeError("Red ajena al laboratorio: se cancela la operación.")
        expected_port = "8012" if service == "api" else "18182"
        bindings = item["HostConfig"]["PortBindings"]
        published = [v for values in bindings.values() for v in (values or [])]
        if published != [{"HostIp": "127.0.0.1", "HostPort": expected_port}]:
            raise RuntimeError("Publicación de puertos inesperada.")
        expected_memory = 512 * 2**20 if service == "api" else 2 * 2**30
        expected_cpu = 10**9 if service == "api" else 2 * 10**9
        if item["HostConfig"]["Memory"] != expected_memory or item["HostConfig"]["NanoCpus"] != expected_cpu:
            raise RuntimeError("Los límites efectivos de CPU/RAM no coinciden con el laboratorio.")
        for mount in item.get("Mounts", []):
            if mount.get("Type") != "volume" or mount.get("Name") != PROJECT + "_datos_hito12":
                raise RuntimeError("Montaje ajeno al volumen propio.")
        result[service] = {
            "id": cid, "image_id": item["Image"], "image_tag": item["Config"]["Image"],
            "memory_limit": item["HostConfig"]["Memory"],
            "nano_cpus": item["HostConfig"]["NanoCpus"],
            "restart_count": item["RestartCount"],
        }
    if set(result) != {"api", "influxdb"}:
        raise RuntimeError("Faltan servicios del laboratorio.")
    return result


def metadata(require_commit=True):
    import psutil
    try:
        commit = command(["git", "rev-parse", "HEAD"])
        status = command(["git", "status", "--porcelain", "--", *SOURCE_PATHS])
    except RuntimeError:
        if require_commit:
            raise RuntimeError("Crear un commit local del código antes de medir.") from None
        commit, status = None, "sin commit"
    if require_commit and status:
        raise RuntimeError("Hay código/configuración sin commit. Guardar un commit antes de medir.")
    docker_info = local_docker()
    own = containers()
    versions = {"influxdb": command(["docker", "exec", own["influxdb"]["id"], "influxdb3", "--version"]),
                "api": json.loads(command(["docker", "exec", own["api"]["id"], "python", "-c",
                    "import json; from app.build_info import build_info; print(json.dumps(build_info()))"]))}
    from app.build_info import build_info
    expected = build_info()
    if any(versions["api"][key] != expected[key] for key in ("app_files_sha256", "requirements_sha256")):
        raise RuntimeError("La API desplegada no coincide con el código/dependencias actuales. Reconstruir solo Hito 12 antes de una nueva línea base.")
    return {"date_utc": now(), "commit": commit, "source_sha256": source_fingerprint(),
            "code_dirty": bool(status), "platform": platform.platform(),
            "python": platform.python_version(), "logical_cpus": psutil.cpu_count(),
            "memory_total_bytes": psutil.virtual_memory().total,
            "machine_id_sha256": digest(platform.node()),
            "docker": docker_info, "containers": own, "versions": versions}


def sql(client, query):
    response = client.get(INFLUX + "/api/v3/query_sql",
                          params={"db": DATABASE, "q": query, "format": "json"}, timeout=30)
    response.raise_for_status()
    rows = response.json()
    if not isinstance(rows, list):
        raise RuntimeError("Formato SQL inesperado")
    return rows


def identity(client, expected_mode=None):
    response = client.get(API + "/lab/identity", timeout=5)
    response.raise_for_status()
    value = response.json()
    if value.get("lab") != PROJECT or value.get("database") != DATABASE:
        raise RuntimeError("El destino no corresponde a Hito 12.")
    if expected_mode and value.get("mode") != expected_mode:
        raise RuntimeError("Modo de API distinto del requerido.")
    return value

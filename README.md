
# Hito 12 — Grupo 09 — Pruebas de carga y optimización

Laboratorio del Fixture Mundial 2030 basado en el flujo de estadísticas del Hito 11. Se utiliza una API aislada conectada a InfluxDB 3 para medir rendimiento, contrastar una optimización y comprobar la integridad de los datos.

**Estado del proyecto:** pruebas de carga, comparación de rendimiento y validación de integridad ejecutadas y publicadas. La optimización fue evaluada mediante tres repeticiones por variante y las conclusiones se documentaron con evidencia real.

Para continuar el trabajo en otra máquina, consultar [el estado de traspaso](docs/TRASPASO.md). Para conocer los resultados finales, consultar [las conclusiones](docs/conclusiones.md).

## Resultados del experimento

Se prepararon **51.840 registros sintéticos** y se compararon dos variantes:

- **Línea base:** conexiones HTTP sin reutilización.
- **Optimización (`pooled`):** reutilización de conexiones HTTP hacia InfluxDB.

Las dos variantes utilizaron el mismo escenario: hasta 4 solicitudes simultáneas, 8 llegadas por segundo durante sostenimiento, 5 segundos de calentamiento, 10 segundos de rampa y 30 segundos de sostenimiento. Se realizaron **3 repeticiones por variante**.

| Métrica | Línea base | Optimizada | Variación |
|---|---:|---:|---:|
| Latencia p50 | 44,862 ms | 20,841 ms | -53,54 % |
| Latencia p95 | 57,916 ms | 24,386 ms | -57,89 % |
| Latencia p99 | 64,515 ms | 26,745 ms | -58,54 % |
| Latencia media | 46,214 ms | 21,324 ms | -53,86 % |
| Throughput | 8 ops/s | 8 ops/s | Sin cambios |
| Errores | 0 | 0 | Sin cambios |

Los valores de latencia corresponden a las medianas de las métricas de cada repetición durante la fase de sostenimiento.

**Resultado:** la optimización redujo las latencias observadas sin introducir errores en el escenario ensayado. La comprobación final confirmó la integridad de los 51.840 registros.

**Limitaciones:** la carga se limitó a 8 operaciones por segundo, por lo que no se midió la capacidad máxima del sistema. Cada repetición tuvo 240 solicitudes en sostenimiento y el p99 dispone de pocas observaciones de cola. También pueden existir efectos de caché u orden de ejecución. Se registró una pequeña regresión en el p95 del retraso de despacho. Los resultados no deben extrapolarse automáticamente a producción.

### Evidencia experimental

- [Preparación del dataset](docs/evidencia/20261104T011338609443Z_preparacion/preparation.json)
- [Línea base — tres repeticiones](docs/evidencia/20261104T011554960995Z_baseline/experiment.json)
- [Hipótesis de optimización](docs/evidencia/20261104T012248028457Z_pooled/hypothesis.json)
- [Comparación detallada y decisión del equipo](docs/evidencia/20261104T012248028457Z_pooled/comparison.md)
- [Comparación JSON](docs/evidencia/20261104T012248028457Z_pooled/comparison.json)
- [Comparación CSV](docs/evidencia/20261104T012248028457Z_pooled/comparison.csv)
- [Integridad final](docs/evidencia/20261104T012635878386Z_integridad/integrity.json)
- [Conclusiones](docs/conclusiones.md)

Las carpetas de cada repetición conservan métricas de carga y API, solicitudes individuales, recursos del sistema, plan de carga y comprobaciones de integridad.

## Qué incluye

- API de estadísticas derivada del código de Hito 11, conservando la consulta original.
- Docker Compose exclusivo de Hito 12, con límites de CPU/RAM y puertos locales.
- Generador determinista de 51.840 registros sintéticos y un oráculo independiente de la API.
- Carga progresiva y tres repeticiones por variante.
- Métricas de latencia, percentiles, throughput, errores, CPU y RAM.
- Validación de respuestas y del dataset antes y después de cada repetición.
- Comparación automática en Markdown, CSV y JSON.
- Propuesta de Data Mart y análisis de alternativa relacional.
- Matriz de requisitos RF1–RF16 y RNF1–RNF14.

Para equipos de **8 GiB**, se incluye un [perfil compacto aislado](docs/perfil_compacto.md), limitado a 960 MiB de memoria en contenedores y 4.320 registros. Sus condiciones no deben mezclarse con las mediciones del escenario estándar.

## Requisitos del entorno

- Git.
- Python 3.13 de 64 bits, con el lanzador `py`.
- Docker Desktop iniciado en modo contenedores Linux.
- Al menos 4 GiB de memoria disponibles en Windows.
- Al menos 4 GiB asignados al daemon de Docker.
- Al menos 5 GiB de espacio libre.

Estos requisitos son controles iniciales conservadores, no una garantía de capacidad.

El laboratorio limita InfluxDB a 2 CPU y 2 GiB de RAM, y la API a 1 CPU y 512 MiB. El generador de carga se ejecuta en Windows y también se monitorea.

## Reproducción del experimento

Clonar el repositorio y abrir PowerShell en la carpeta raíz del proyecto.

No reutilizar contenedores, volúmenes, archivos `.env` ni credenciales del Hito 11. Los directorios `.venv`, `.localtmp`, `.runtime` y los datos locales generados no deben copiarse entre entornos.

### 1. Instalar y verificar

Si PowerShell bloquea la ejecución de scripts:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Instalar dependencias y verificar el código:

```powershell
.\scripts\instalar.ps1
.\scripts\verificar_entorno.ps1
```

El código y la configuración deben estar asociados a un commit de Git antes de medir. Al clonar este repositorio, no es necesario crear un nuevo commit si no se efectuaron modificaciones.

### 2. Iniciar y preparar datos

```powershell
.\scripts\iniciar_entorno.ps1
.\scripts\preparar_datos.ps1
.\scripts\validar_integridad.ps1
```

El script de inicio construye la API y utiliza la imagen fijada de InfluxDB.

Puertos locales:

- API: `127.0.0.1:8012`
- InfluxDB: `127.0.0.1:18182`
- Documentación de la API: http://127.0.0.1:8012/docs

La preparación es idempotente para el mismo dataset: utiliza las mismas claves y marcas temporales. También controla que el volumen local corresponda al escenario esperado.

Los archivos de `.runtime/` y `datos/generados/` deben mantenerse durante el experimento.

### 3. Prueba de humo y línea base

```powershell
.\scripts\ejecutar_humo.ps1
.\scripts\ejecutar_linea_base.ps1
```

La prueba de humo comprueba el funcionamiento inicial, pero no reemplaza la línea base completa.

La línea base utiliza `config/carga.json`, con 3 repeticiones, una tasa objetivo de 8 llegadas por segundo y 30 segundos de sostenimiento.

Para consultar los resultados de la última línea base:

```powershell
$base = (Get-Content .\.runtime\last_baseline.json -Raw | ConvertFrom-Json).path

Get-Content (Join-Path $base 'trial_01\load.json')
Get-Content (Join-Path $base 'trial_01\resources.json')
```

Los percentiles finales excluyen las fases de calentamiento y rampa.

Existe también `config/carga_extendida.json`, que contempla 150 segundos de sostenimiento y 1.200 solicitudes previstas por repetición.

**El escenario extendido es opcional y no se incluyó en las mediciones publicadas.** Si se utiliza, ambas variantes deben ejecutarse con esa misma configuración.

### 4. Registrar hipótesis y ejecutar la optimización

Antes de activar la variante candidata, revisar las métricas de la línea base.

La latencia de la dependencia comprende transporte, espera y consulta; no constituye una medición aislada del tiempo de ejecución SQL.

```powershell
$hipotesis = Read-Host 'Hipotesis sustentada en la linea base y resultado esperado'

$evidencia = Join-Path $base 'trial_01\load.json'

.\scripts\ejecutar_prueba_optimizada.ps1 -LineaBase $base -Hipotesis $hipotesis -Evidencia $evidencia
```

El script registra la hipótesis antes de ejecutar la variante `pooled`, conserva las condiciones comparables y genera:

- `comparison.md`
- `comparison.csv`
- `comparison.json`

La optimización no se considera válida solo por estar implementada: su aceptación depende de las mediciones, el comportamiento de los recursos, los errores y la integridad.

### 5. Validar integridad y cerrar

```powershell
.\scripts\validar_integridad.ps1
.\scripts\limpiar_datos_de_prueba.ps1
```

La limpieza detiene el laboratorio para permitir su reutilización. No elimina contenedores, volúmenes, datos ni evidencias.

Para continuar posteriormente:

```powershell
.\scripts\reanudar_entorno.ps1
```

Al reanudar, se recomienda volver a validar integridad.

Antes de publicar nuevos ensayos, comprobar que las evidencias no contengan credenciales y que los documentos distingan resultados medidos, objetivos de configuración, hipótesis y propuestas conceptuales.

## Documentación

| Documento | Contenido |
|---|---|
| [Procedencia](docs/procedencia.md) | Repositorio de referencia, archivos reutilizados y diferencias |
| [Flujo y escenario](docs/flujo_y_escenario_de_carga.md) | Consumidor, distribución, volumen, tasa, rampa y límites |
| [Línea base](docs/linea_base.md) | Método, metadatos, percentiles y trazabilidad |
| [Hipótesis y optimización](docs/hipotesis_y_optimizacion.md) | Candidato, método de contrastación, costos y decisión |
| [Integridad y limitaciones](docs/integridad_y_limitaciones.md) | Oráculo, hashes, conteos y límites |
| [Data Mart](docs/integracion_data_mart.md) | Pregunta analítica, grano, ETL, frescura y validación |
| [Alternativa relacional](docs/comparacion_relacional.md) | Modelo conceptual, consulta, garantías y condiciones de conveniencia |
| [Entorno y diagnóstico](docs/entorno_y_diagnostico.md) | Docker, recursos, seguridad y recuperación |
| [Evidencias](docs/evidencia/README.md) | Organización y significado de los resultados |
| [Matriz de requisitos](docs/matriz_requisitos.md) | Cobertura RF/RNF y estado de verificaciones |
| [Conclusiones](docs/conclusiones.md) | Resultados, decisión del equipo y limitaciones |

El diseño del Data Mart y la alternativa relacional están documentados, pero no se ejecutaron experimentos de rendimiento sobre esas alternativas. No deben confundirse con los resultados medidos en InfluxDB.

## Ejecución en otros sistemas operativos

Los comandos equivalentes están disponibles mediante:

```bash
python -m hito12.cli --help
```

En macOS/Linux, con Python 3.13 disponible:

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev-lock.txt
.venv/bin/python -m pytest -q
.venv/bin/python -m hito12.cli doctor
```

La CLI ofrece las operaciones `up`, `prepare`, `integrity`, `run` y `stop`.

Los resultados experimentales publicados corresponden al laboratorio ejecutado en Windows con Docker Desktop; no constituyen una medición de rendimiento en macOS o Linux.

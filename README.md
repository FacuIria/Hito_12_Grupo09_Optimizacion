# Hito 12 — Grupo 09 — Pruebas de carga y optimización

Laboratorio del Fixture Mundial 2030 preparado para ejecutarse en una notebook con Windows, Python 3.13 y Docker Desktop (contenedores Linux). Se mide el endpoint de estadísticas de Hito 11 en una copia aislada con InfluxDB 3. La variante candidata reutiliza conexiones HTTP; su beneficio debe comprobarse con mediciones.

**Estado:** implementación y verificaciones locales preparadas. Las pruebas de carga contra InfluxDB, la comparación de rendimiento y la conclusión experimental están **pendientes de ejecución en la notebook**. Los tests con dobles de prueba no constituyen evidencia de rendimiento del motor. Ver [verificación local](docs/verificacion_local.md) y [matriz de requisitos](docs/matriz_requisitos.md).

## Qué incluye

- API de estadísticas derivada del código de Hito 11, con consulta original conservada.
- Docker Compose exclusivo de Hito 12, con límites de CPU/RAM y puertos locales.
- Generador determinista de 51.840 registros sintéticos y un oráculo independiente de la API.
- Carga progresiva, tres repeticiones por variante, percentiles, throughput, errores y muestreo de recursos.
- Validación de cada respuesta y de todo el dataset antes y después de cada repetición.
- Comparación en Markdown, CSV y JSON que rechaza escenarios incompatibles.
- Propuesta de Data Mart, alternativa relacional y auditoría RF1–RF16/RNF1–RNF14.

## Preparación en tu notebook

Copiar el repositorio completo **sin** `.venv`, `.localtmp` ni `.runtime`, o clonarlo cuando se haya publicado. No copiar contenedores, volúmenes, `.env` ni credenciales de Hito 11. Abrir PowerShell en la raíz de Hito 12.

Requisitos: Git; Python 3.13 de 64 bits con el lanzador `py`; Docker Desktop iniciado en modo Linux; al menos 4 GiB disponibles en Windows antes de iniciar, 4 GiB asignados al daemon y 5 GiB de disco libre. Estos son controles iniciales conservadores, no una garantía de capacidad. El laboratorio limita el motor a 2 CPU/2 GiB y la API a 1 CPU/512 MiB. El generador se ejecuta en Windows y también se monitorea.

Si PowerShell bloquea scripts descargados, permitirlos **solo en la sesión actual**:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Instalar dependencias fijadas y comprobar el código:

```powershell
.\scripts\instalar.ps1
.\scripts\verificar_entorno.ps1
```

Antes de medir, el código debe tener un commit local. Si recibiste una carpeta sin `.git`, ejecutar `git init` y configurar tu identidad de Git. Revisar primero qué se versionará:

```powershell
git status --short
git add .
git diff --cached --stat
git commit -m "Preparar laboratorio reproducible del Hito 12"
```

Si el código ya viene en un commit y no tiene cambios, no hace falta otro. Las herramientas rechazan código o configuración sin commit al ejecutar pruebas reales. Los datasets grandes, entornos virtuales y archivos privados están excluidos por `.gitignore`.

## Orden de ejecución

### 1. Iniciar y preparar

```powershell
.\scripts\iniciar_entorno.ps1
.\scripts\preparar_datos.ps1
.\scripts\validar_integridad.ps1
```

`iniciar_entorno.ps1` construye la API y descarga la imagen fijada de InfluxDB. La primera ejecución necesita Internet y puede demorar. Los puertos son `127.0.0.1:8012` para la API y `127.0.0.1:18182` para el motor. No se usan puertos, redes, volúmenes ni servicios de Hito 11. La documentación interactiva está en <http://127.0.0.1:8012/docs>.

La preparación es idempotente para el mismo dataset: reescribe las mismas claves y timestamps, luego verifica todos los registros. Rechaza un volumen con datos sin manifiesto local o con otra configuración. Los archivos `datos/generados/` y `.runtime/` se producen en la notebook y deben conservarse durante el experimento.

### 2. Prueba pequeña y línea base

```powershell
.\scripts\ejecutar_humo.ps1
.\scripts\ejecutar_linea_base.ps1
```

El humo es una comprobación técnica, no la comparación final. La línea base final usa `config/carga.json`: 4 solicitudes simultáneas como máximo, 8 llegadas/s en sostenimiento, 5 s de calentamiento, 10 s de rampa, 30 s de sostenimiento y 3 repeticiones. Son **parámetros objetivo**, no resultados medidos.

Cada ejecución imprime la carpeta de evidencia. Para consultar la última línea base:

```powershell
$base = (Get-Content .\.runtime\last_baseline.json -Raw | ConvertFrom-Json).path
Get-Content (Join-Path $base 'trial_01\load.json')
Get-Content (Join-Path $base 'trial_01\resources.json')
```

Los percentiles finales excluyen calentamiento y rampa. Si hay falta de memoria, CPU sostenida, respuestas incorrectas o demasiados errores, el ensayo se interrumpe y conserva su evidencia. No bajar las protecciones para forzar una ejecución. Ver [entorno y diagnóstico](docs/entorno_y_diagnostico.md).

### 3. Registrar la hipótesis y ejecutar la candidata

Revisar la línea base antes de atribuir el costo al establecimiento de conexiones. Comparar latencia del cliente, API, llamada al motor y recursos. El tiempo de dependencia incluye transporte, espera y consulta: no es tiempo SQL puro. Ver [hipótesis y optimización](docs/hipotesis_y_optimizacion.md).

Ingresar una explicación propia basada en la salida real; la referencia debe apuntar a un archivo existente de esa línea base:

```powershell
$hipotesis = Read-Host 'Hipotesis sustentada en la linea base y resultado esperado'
$evidencia = Join-Path $base 'trial_01\load.json'
.\scripts\ejecutar_prueba_optimizada.ps1 -LineaBase $base -Hipotesis $hipotesis -Evidencia $evidencia
```

El script guarda esa hipótesis **antes** de cambiar la API a `pooled`; conserva el motor y la imagen API. Repite el mismo plan, semilla, dataset, recursos y tres repeticiones. La comparación se genera automáticamente en la carpeta `..._pooled/`: `comparison.md`, `comparison.csv`, `comparison.json`. No se afirma mejora automáticamente.

Si la evidencia apunta a otro problema, no declarar confirmado el pool. Se puede probar como hipótesis exploratoria y rechazarla si corresponde, o diseñar otra optimización y obtener una nueva línea base. El candidato está preparado de antemano para facilitar la ejecución; eso no equivale a una optimización validada.

### 4. Cierre de la entrega

```powershell
.\scripts\validar_integridad.ps1
.\scripts\limpiar_datos_de_prueba.ps1
```

La limpieza elegida consiste en **detener y reutilizar** el laboratorio. No borra datos, contenedores, redes ni evidencias. Para continuar: `.\scripts\reanudar_entorno.ps1`; después, volver a validar integridad. No preparar otra vez los datos entre baseline y pooled.

Completar [conclusiones](docs/conclusiones.md) y [matriz de requisitos](docs/matriz_requisitos.md) con los archivos reales. Revisar los resultados antes de versionarlos. Agregar las evidencias y documentos con Git, crear un commit y subir al repositorio **de Hito 12**. La publicación remota no forma parte de los scripts.

## Documentación

| Documento | Contenido |
|---|---|
| [Procedencia](docs/procedencia.md) | Repositorio/commit de referencia, archivos reutilizados y diferencias |
| [Flujo y escenario](docs/flujo_y_escenario_de_carga.md) | Consumidor, distribución, volúmenes, tasa, rampa y límites |
| [Línea base](docs/linea_base.md) | Método, metadatos, percentiles y trazabilidad |
| [Hipótesis y optimización](docs/hipotesis_y_optimizacion.md) | Candidato, prueba contrastable, costos y decisión |
| [Integridad y limitaciones](docs/integridad_y_limitaciones.md) | Oráculo, hash completo, conteos y límites |
| [Data Mart](docs/integracion_data_mart.md) | Pregunta, grano, ETL, frescura, duplicados y validación |
| [Alternativa relacional](docs/comparacion_relacional.md) | Modelo, consulta, garantías y condiciones de conveniencia |
| [Entorno](docs/entorno_y_diagnostico.md) | Docker, recursos, seguridad, recuperación y diagnóstico |
| [Evidencias](docs/evidencia/README.md) | Estructura y significado de cada resultado |
| [Requisitos](docs/matriz_requisitos.md) | Cobertura preparada y comprobación pendiente |

Los comandos equivalentes multiplataforma están disponibles mediante `python -m hito12.cli --help`. El despliegue real en Docker no se ha ejecutado en el entorno de preparación.

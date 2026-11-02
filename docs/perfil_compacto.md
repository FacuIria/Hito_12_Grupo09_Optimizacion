# Laboratorio compacto para notebook de 8 GiB

El umbral original de 4 GiB libres era una precaución del laboratorio de 2,5 GiB de contenedores, no un requisito del PDF. Tras observar que el host no llega a ese margen, se diseñó un experimento diferente, de menor tamaño, con límites propios. No se omite el preflight del perfil estándar ni se comparan resultados entre perfiles.

| Parámetro | Compacto |
|---|---|
| Motor | InfluxDB 3.12.2 Core, 1 CPU, 768 MiB |
| API | Misma imagen/código, 0,5 CPU, 192 MiB |
| Memoria interna del motor | Ejecución 128 MB, snapshot 64 MB, 1 thread I/O y 1 DataFusion |
| Datos | 6 partidos, 2 equipos, 30 minutos, muestras cada 5 s: 4.320 registros sintéticos |
| Carga final ofrecida | 2 llegadas/s, máximo 2 simultáneas |
| Fases | 5 s calentamiento, 10 s rampa, 60 s sostenimiento |
| Repeticiones | 3 por variante, descanso de 5 s |
| Llegadas previstas | 139 por repetición: 10 calentamiento, 9 rampa, 120 sostenimiento |
| Distribución | 80% de probabilidad sobre 4 partidos calientes; cuatro resoluciones |
| Memoria host | Al menos 1.536 MiB antes de construir/arrancar; 1.024 MiB antes de preparar/medir y durante carga |
| Interrupción adicional | CPU host ≥85% en 2 muestras; RAM de contenedor ≥85%; error/integridad/monitor según configuración |

El máximo conjunto de memoria de contenedores es 960 MiB, inferior a los 1.536 MiB requeridos inicialmente. El margen es una precaución, no una garantía de capacidad. Se vuelve a verificar memoria después de construir, después de descargar el motor y tras arrancar; se controla antes de cada lote de preparación. El generador guarda CPU/RAM del host y de los contenedores durante la carga. No ejecutar simultáneamente con el perfil estándar.

## Reproducción

Seleccionar el perfil **antes** de invocar Python, manteniéndolo para todo el experimento:

```powershell
$env:HITO12_PROFILE = 'compacto'
.\scripts\verificar_entorno.ps1
.\scripts\iniciar_entorno.ps1
.\scripts\preparar_datos.ps1
.\scripts\validar_integridad.ps1
.\scripts\ejecutar_carga.ps1 -Modo baseline -Configuracion config/humo_compacto.json
.\scripts\ejecutar_carga.ps1 -Modo baseline -Configuracion config/carga_compacto.json
$base = (Get-Content .\.runtime\compacto\last_baseline.json -Raw | ConvertFrom-Json).path
$hipotesis = Read-Host 'Hipotesis fundada en la linea base'
$evidencia = Join-Path $base 'trial_01\load.json'
.\scripts\ejecutar_carga.ps1 -Modo pooled -Configuracion config/carga_compacto.json -LineaBase $base -Hipotesis $hipotesis -Evidencia $evidencia
.\scripts\validar_integridad.ps1
.\scripts\limpiar_datos_de_prueba.ps1
```

En macOS/Linux: `export HITO12_PROFILE=compacto` y usar `.venv/bin/python -m hito12.cli` con `doctor`, `up`, `prepare`, `integrity`, `run --mode baseline --config config/humo_compacto.json`, `run --mode baseline`, `run --mode pooled --baseline RUTA --hypothesis TEXTO --evidence ARCHIVO`, `integrity` y `stop`.

Compose: `compose.compacto.yaml`; volumen: `hito12-g09_datos_hito12_compacto`; datos: `datos/generados/compacto/`; estado: `.runtime/compacto/`. Conserva el proyecto exclusivo Hito 12 y la red interna, y añade una red bridge propia `hito12-g09_acceso` para publicar puertos loopback 8012/18182 en Docker Desktop. Esta segunda red permite también salida de los servicios; el laboratorio no queda aislado de Internet. No comparte redes ni datos con Hito 11. La identidad, límites y volumen efectivos se validan antes de escribir o medir. El código/configuración debe estar en un commit antes de preparar datos.

## Interpretación

Esta carga permite contrastar el transporte HTTP sobre el flujo real y verificar integridad, no demostrar escalabilidad o saturación del motor. Solo hay 120 solicitudes previstas en sostenimiento por repetición: p99 es exploratorio. No ocultar errores ni corridas interrumpidas. Mantener iguales dataset, agenda, recursos, imágenes y versión entre baseline y pooled. Una mejora nula o una regresión también deben informarse. El escenario estándar y el extendido siguen disponibles como escenarios no ejecutados si no se miden.

Frente a la proyección ilustrativa de 1.123.200 puntos documentada para el sistema completo, 4.320 son aproximadamente el 0,385%; no se extrapolan linealmente tiempos ni capacidad. El dataset compacto representa ventanas de 30 minutos, no partidos completos. Los límites y la elección de ventanas reducidas deben acompañar cualquier conclusión.

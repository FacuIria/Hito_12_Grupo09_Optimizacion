# Línea base y método de medición

**Estado: pendiente de ejecutar con InfluxDB en la notebook.** No hay valores de latencia o throughput de Hito 12 para completar esta sección todavía.

La base usa la consulta original del adaptador de Hito 11 y `httpx.get` por operación. No se utiliza la API original desplegada. La instrumentación, dataset y límites son idénticos en ambas variantes.

## Trazabilidad

`experiment.json` identifica fecha UTC, commit, hash del contenido de código/configuración, Python del generador, plataforma, CPU lógica, memoria total, identificador de máquina hasheado, versión y recursos de Docker, IDs/etiquetas de imágenes, límites efectivos y versiones observadas dentro de los contenedores. No recopila variables de entorno privadas ni tokens.

Cada ejecución usa una carpeta nueva; no sobrescribe resultados anteriores. El manifiesto de datos guarda parámetros, conteos y hashes esperados. Los archivos `plan.json` guardan la agenda exacta. Un hash de código distinto, otra configuración o un dataset distinto exige otra línea base.

Además se comparan los hashes de los módulos API y del archivo de dependencias **dentro del contenedor** con los del repositorio. Así se rechaza una imagen desactualizada aunque el código local tenga commit. Los hashes de texto normalizan CRLF/LF para conservar significado entre Windows y Linux.

## Qué mide cada capa

| Capa | Método y unidad | Alcance |
|---|---|---|
| Generador | `perf_counter`, ms desde envío hasta lectura completa del cuerpo | Incluye HTTP y transferencia; excluye validación posterior |
| API | `X-Api-Ms`, ms alrededor del procesamiento ASGI | Incluye espera y serialización hasta producir la respuesta; no toda la transferencia al cliente |
| Dependencia | `X-Dependency-Ms`, ms alrededor de la llamada SQL HTTP | Transporte, conexión/pool, consulta y decodificación; **no** tiempo SQL puro |
| API | Contadores acumulados `/lab/metrics` antes/después | Solicitudes de estadísticas, errores de dependencia, suma del tiempo de llamada |
| Motor/API Docker | `docker stats` sobre sus IDs propios | CPU, memoria, red y disco observados; red/disco son contadores del contenedor |
| Host/generador | psutil | CPU host, RAM disponible, CPU/RSS del generador |

Las estadísticas internas de ejecución del motor y el tiempo exacto de espera de pool no se instrumentan. No restar percentiles entre capas como si provinieran de la misma solicitud; usar `requests.csv` para relaciones por operación. Docker y psutil no siempre usan el mismo denominador de CPU: un proceso/contenedor puede superar 100% al usar varios núcleos.

## Resumen y unidades

Se calcula mínimo, media, mediana, p90, p95, p99 y máximo mediante interpolación lineal en la lista ordenada. Se conserva cada operación; no se descartan latencias de errores. También se calculan latencias exclusivamente exitosas. Una distribución sin muestras se representa como `null`, nunca cero.

El resumen principal usa solicitudes **programadas durante sostenimiento**. Throughput exitoso = solicitudes de esa cohorte validadas y terminadas antes de finalizar la ventana / segundos de sostenimiento. Los éxitos que terminan durante el drenaje se muestran por separado. Los errores se dividen por operaciones completadas; las no enviadas tienen conteo propio. El tiempo total con drenaje también se conserva.

`comparison.md` informa la mediana de cada métrica de las repeticiones y su rango mínimo–máximo. No promedia percentiles para presentarlos como percentil conjunto. Con tres repeticiones no se afirma significación estadística. Mejoras pequeñas pueden ser ruido.

## Condiciones antes/después

No cambiar máquina, carga externa deliberadamente, versión, dataset, consulta, tasa, agenda, número de repeticiones o recursos. La API se recrea para cambiar modo, usando la misma imagen; el motor se mantiene. La validación completa previa calienta el motor en ambas variantes. La fase de calentamiento intenta estabilizar conexiones y cachés, sin garantizar el mismo estado interno.

El orden baseline→pooled puede favorecer a la segunda variante por caché/temperatura/actividad externa. Para estudiar esa sensibilidad se pueden ejecutar nuevos pares completos, documentando el orden; no se deben seleccionar solo las mejores repeticiones. Conservar también corridas fallidas y resultados adversos.

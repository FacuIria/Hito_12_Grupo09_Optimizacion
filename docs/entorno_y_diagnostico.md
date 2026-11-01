# Entorno, límites y diagnóstico

## Aislamiento

Proyecto fijo `hito12-g09`; red interna `hito12-g09_laboratorio`; volumen `hito12-g09_datos_hito12`. Servicios `api` e `influxdb` con etiqueta `edu.fixture.hito=12`. No se usan redes externas ni montajes de carpetas con datos previos. El controlador valida identidad, puertos, red, montajes y límites efectivos antes de cargar/medir.

API: puerto local 8012, 1 CPU, 512 MiB. Motor: puerto local 18182, 2 CPU, 2 GiB. InfluxDB tiene dos threads de I/O, dos de DataFusion, pool de ejecución de 512 MB y umbral de snapshot de 256 MB. Docker limita el proceso completo. Las opciones de memoria internas no equivalen al consumo total del motor.

Se rechazan contextos Docker remotos y variables `DOCKER_HOST`/`DOCKER_CONTEXT`. Usar el contexto local de Docker Desktop. Los comandos de Compose especifican proyecto y archivo, evitando actuar sobre el directorio o proyecto equivocado. No se requieren credenciales. Los puertos solo se publican en loopback; el modo sin autenticación es exclusivo del laboratorio local.

## Fallos frecuentes

| Mensaje/situación | Acción |
|---|---|
| `docker` no encontrado | Instalar Docker Desktop en la notebook, iniciarlo y abrir otra terminal |
| Daemon no disponible / contenedores Windows | Iniciar Docker Desktop y seleccionar contenedores Linux |
| Menos de 4 GiB libres al inicio | Cerrar aplicaciones propias y revisar asignación de RAM; no detener servicios de Hito 11 desde estos scripts |
| Puerto ocupado | Identificar el uso; no matar procesos ni cambiar puertos de Hito 11. Liberar el puerto propio o ajustar Hito 12 de forma coherente antes de crear una nueva línea base |
| Laboratorio ya existe | Usar `reanudar_entorno.ps1`; si ya está corriendo, pasar a preparar/validar |
| Datos sin manifiesto local | Recuperar `.runtime/dataset-lock.json` y `datos/generados/` del mismo laboratorio. No escribir ni borrar un volumen desconocido |
| Imagen o código cambió entre variantes | Crear commit del código y medir una línea base nueva; no mezclar resultados |
| Rechazo por datos/escenario distinto | Restaurar la configuración del par o iniciar un experimento nuevo documentado |
| Error de recursos o integridad durante carga | Conservar evidencia, corregir la causa y repetir ambas variantes bajo las mismas condiciones |
| `403` al subir a GitHub | Revisar autenticación/permisos de Git por separado; no afecta la ejecución local |

Diagnóstico de solo lectura del laboratorio:

```powershell
docker compose --project-name hito12-g09 --file compose.yaml ps
docker compose --project-name hito12-g09 --file compose.yaml logs --tail 80 api influxdb
Invoke-RestMethod http://127.0.0.1:8012/lab/identity
```

Revisar/redactar cualquier salida antes de publicarla. Los scripts no guardan dumps de configuración del host ni variables privadas. Los logs de servicios están rotados a dos archivos de 10 MB.

## Repetición y limpieza

La estrategia soportada es conservar/reutilizar el dataset. `limpiar_datos_de_prueba.ps1` ejecuta únicamente `stop` de los dos servicios Hito 12. `reanudar_entorno.ps1` usa `start`: no reconstruye contenedores. No se incluye un borrado de volumen. Para cambiar el dataset de un laboratorio ya poblado hay que diseñar explícitamente otro entorno aislado o un procedimiento de reinicialización restringido; no se fuerza con limpiezas globales.

Las corridas nuevas escriben carpetas nuevas. No editar CSV/JSON medidos para que una comparación pase. Un ensayo fallido puede ayudar a explicar un límite, pero no acredita el mismo escenario completado.

Si se corrigió código y la API desplegada quedó desactualizada, guardar el commit y reconstruir **solo** la API propia antes de una nueva línea base:

```powershell
$env:HITO12_MODE = 'baseline'
docker compose --project-name hito12-g09 --file compose.yaml up -d --no-deps --build api
```

Esto invalida cualquier comparación con una línea base anterior. El motor y el volumen se conservan; verificar integridad antes de volver a medir.

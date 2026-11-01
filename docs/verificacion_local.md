# Verificación local del código

## Auditoría posterior en macOS — 1 de noviembre de 2026

Python **3.13.18**, macOS ARM64, 8 CPU lógicas y 8 GiB de RAM física. Resultado real después de las correcciones: **44 tests aprobados**, una advertencia de deprecación Starlette/AnyIO, sin fallos. Evidencia con comandos, códigos de salida, commit de partida, estado modificado y hash del código probado: [verificacion_macos.json](evidencia/verificacion_macos.json). La evidencia histórica de Windows que aparece debajo corresponde a otra revisión.

Se comprobaron también compilación Python, configuración de Compose y ayuda de la CLI. Las 21 dependencias instaladas pasaron la comprobación de compatibilidad de `uv pip check`. Se generaron **51.840 registros** localmente, sin escribirlos en InfluxDB. Se verificó mediante `docker manifest inspect` que las imágenes fijadas de InfluxDB y Python existen para Linux ARM64 y AMD64; esto no verifica que sus servicios arranquen. Las nuevas pruebas comprueban rechazo de servicios ajenos antes de detener/reanudar, rechazo de cambios de entorno antes de activar pooled, conservación de metadatos y escrituras inciertas tras timeout, y planificación del escenario extendido sin aumentar tasa/concurrencia.

El diagnóstico final observó **1,18 GiB disponibles en el host** y 5.155.180.544 bytes asignados al daemon Docker. El intento real de `up` fue rechazado por el control de **4.096 MiB libres en el host**, antes de construir o iniciar servicios. No se redujeron los umbrales ni se ejecutaron cargas, escrituras o pruebas de rendimiento contra InfluxDB. En esta revisión no se ejecutó PowerShell: esa validación queda cubierta únicamente por la evidencia histórica indicada debajo.

Los primeros intentos de pytest tuvieron restricciones del sandbox para abrir el servidor localhost y un directorio padre temporal aún inexistente. Se creó el directorio y se repitió con permiso para localhost; la ejecución final completa es la registrada en el JSON. Esos intentos no fueron pruebas del motor.

Para continuar: liberar memoria del host sin intervenir Hito 11, repetir `doctor`, revisar/guardar los cambios en un commit y seguir el orden del README. Si la máquina de 8 GiB no alcanza los mínimos, usar otra con más memoria. La disponibilidad de Docker por sí sola no acredita capacidad para ejecutar este laboratorio.

## Verificación histórica en Windows

Fecha: **1 de noviembre de 2026**. Entorno: Windows, Python **3.13.7**. El despliegue usa una imagen Python 3.13.3 fijada; la comprobación del contenedor sigue pendiente.

Resultado real: **37 tests aprobados**, una advertencia de deprecación de la integración Starlette/AnyIO, sin fallos. Salida completa con fecha, comando, código de salida y hash del código: [verificacion_codigo.json](evidencia/verificacion_codigo.json).

Cobertura comprobada:

- Generación determinista, claves únicas y suma de posesión.
- Agregaciones con resultados conocidos; detección de alteraciones y filas duplicadas.
- Normalización UTC independiente de la zona local.
- Contrato de API, validación de parámetros y error seguro de dependencia.
- Misma consulta y forma de respuesta para baseline/pooled.
- Reutilización efectiva de conexión de pooled frente a dos conexiones en baseline, usando un servidor HTTP local de prueba.
- Agenda reproducible, rampa, percentiles, separación de calentamiento, errores, no enviadas y drenaje.
- Ejecución del generador con transporte/recursos simulados: exportación y detención ante respuesta incorrecta.
- Rechazo de comparaciones incompatibles y generación de tablas a partir de fixtures identificadas como datos de test.
- Rechazo de red, volumen, puerto, etiqueta y límites ajenos; rechazo de Docker remoto.
- Identificación de módulos/dependencias desplegados y rechazo de una API desactualizada.
- Estructura aislada de Compose y límites declarados.

Otras verificaciones realizadas: compilación de los módulos Python, `pip check` sin dependencias rotas, ayuda de la CLI, análisis sintáctico de **14 scripts PowerShell** sin errores y generación local de **51.840 registros** con su manifiesto/oráculo. Esa generación **no** equivale a una carga en InfluxDB.

Docker no está disponible en el entorno de preparación. **No se ejecutaron** build de imágenes, arranque de InfluxDB, escritura del dataset en el motor, carga real, validación de la base real ni comparación de rendimiento. Las métricas de fixtures de tests se guardan solo en temporales excluidos de Git y no se presentan como resultados del hito.

Repetir en la notebook con `scripts/instalar.ps1`, seguido del procedimiento del README. Si cambia el código, esta evidencia corresponde al hash registrado, no automáticamente a la revisión posterior.

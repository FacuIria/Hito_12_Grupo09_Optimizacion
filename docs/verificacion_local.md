# Verificación local del código

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

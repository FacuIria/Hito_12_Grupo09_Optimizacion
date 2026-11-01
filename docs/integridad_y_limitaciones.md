# Integridad y limitaciones

## Preparación

El generador usa semilla fija, identificadores y timestamps deterministas. El line protocol lleva precisión explícita `second`, contadores enteros y posesión con dos decimales. Se escribe en lotes de hasta 1.000 registros con `accept_partial=false` y `no_sync=false`.

Se contabilizan registros intentados y confirmados por HTTP; un lote con timeout se clasifica como aceptación desconocida, no como rechazado. La cantidad confirmada no es una cantidad de inserciones nuevas: InfluxDB combina puntos con la misma tabla, tags y timestamp. Reejecutar la preparación del mismo dataset es una operación de upsert idempotente; la verificación posterior determina el estado real.

## Validación de la fuente

Antes y después de cada repetición se consulta el conteo total de la tabla y se leen **todos** los campos de todos los partidos generados, por partido. Se comparan conteos, claves únicas y SHA256 de una representación canónica con el generador. Se verifica el total global para detectar también registros ajenos a los partidos esperados. Un mismo conteo con valores alterados falla.

Clave: `(partido_id, equipo_codigo, sede_id, time)`. Los timestamps SQL sin zona se interpretan como UTC, según el almacenamiento del motor; nunca con la zona local de Windows. Las representaciones con `Z`, `+00:00` y fracciones nulas se normalizan. Los contadores deben ser enteros. La posesión se normaliza a seis decimales para no atribuir corrupción a diferencias de representación flotante.

Esta normalización permite diferencias de posesión menores que la precisión comparada; no es una prueba bit a bit del almacenamiento interno. No se exportan datos sensibles porque el dataset es enteramente sintético.

## Validación de respuestas

El oráculo agrupa los datos generados en Python, independientemente del SQL de la API. Comprueba `AVG`, `MAX`, `SUM`, claves y timestamps para cada partido/resolución. Cada respuesta de carga se compara completa con su hash esperado, incluyendo cantidad de filas; duplicar, omitir o alterar una fila falla. También se revisan partido, ventana, resolución, truncado e identidad del laboratorio. Cualquier inconsistencia detiene la carga.

En este dataset los pases acumulados son monótonos: `MAX` coincide con el último acumulado. En datos con reinicios o correcciones no necesariamente coincide; se requeriría una consulta distinta y otra validación. Los promedios de posesión tienen sentido por muestreo uniforme; no se generalizan a muestras irregulares.

## Límites del experimento

- Se mide un flujo de lectura y un motor, sin escrituras simultáneas ni todos los módulos.
- Los 24 partidos se ubican en una sola ventana de 90 minutos; no se estudia historia extensa, retención ni alta cardinalidad productiva.
- La carga, el generador, Docker Desktop y el sistema operativo comparten hardware. Virtualización, temperatura, ahorro de energía y otras aplicaciones pueden variar.
- El oráculo consume CPU del generador; su tiempo se mide por separado pero puede limitar la emisión. Revisar CPU, atraso y operaciones no enviadas.
- CPU/RAM son muestras discretas. No hay trazas de ejecución SQL ni atribución exacta de CPU por consulta.
- No se prueban caída real de dependencia, recreación de volumen o durabilidad ante corte de energía. No se acredita RF21 de Hito 11.
- Data Mart y alternativa relacional son propuestas documentadas, no implementaciones medidas.
- Las pruebas locales con dobles verifican software; el despliegue Docker y el rendimiento requieren ejecución en la notebook.

**Resultado de integridad contra InfluxDB: pendiente.** Los hashes calculados localmente son valores esperados, no prueba de que la carga ya llegó al motor.

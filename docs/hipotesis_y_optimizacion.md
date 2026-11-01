# Hipótesis y optimización candidata

**Estado:** candidato implementado y probado con servidor HTTP de prueba; hipótesis experimental e impacto en InfluxDB pendientes.

## Observación del código

El adaptador original llama `httpx.get` en cada consulta. La candidata crea un `httpx.Client` por proceso de API y lo cierra al terminar. Se conservan SQL, parámetros, autenticación ficticia local, timeout, contrato, dataset y recursos. El pool admite hasta 16 conexiones y 16 conexiones ociosas, con expiración de 5 s. La carga predeterminada limita la concurrencia a 4.

Los tests de conexiones verifican que dos consultas de baseline usan conexiones distintas y dos de la candidata reutilizan una conexión HTTP/1.1 en un servidor local. **No** cuantifican el costo ni demuestran que sea el cuello de botella real.

## Hipótesis contrastable a completar tras la base

1. Revisar `trial_*/load.json`, `requests.csv`, `api_metrics.json` y `resources.json`.
2. Identificar qué tiempos/costos predominan y si el generador cumple la agenda.
3. Explicar por qué el costo de crear cliente/conexión es un candidato plausible. Si los datos apuntan a consultas o recursos del motor, dejar esa limitación explícita.
4. Registrar el efecto esperado: por ejemplo menor tiempo de llamada a dependencia y menor CPU de API, manteniendo respuestas, errores y tasa ofrecida. No fijar un porcentaje como resultado.
5. Ejecutar pooled sin reconstruir la imagen ni cambiar el motor. Comparar las tres repeticiones y revisar integridad.

El script requiere un texto de hipótesis y un archivo real de la línea base. Guarda fecha y hash de esa evidencia antes de activar pooled. El requisito de tener una hipótesis no garantiza su calidad: el equipo debe fundamentarla. El código candidato preexistente se describe como preparación, no como intervención derivada de mediciones que todavía no existen.

## Archivos afectados

- `app/upstream_influx3.py`: referencia original conservada.
- `app/adapter.py`: instrumentación común y elección entre llamada efímera y cliente persistente.
- `app/main.py`: ciclo de vida y contrato del flujo aislado.
- `compose.yaml`: `HITO12_MODE` selecciona variante; el resto se mantiene.

## Costos y decisión

Reutilizar conexiones retiene sockets/memoria y requiere cerrar el cliente. El límite del pool puede introducir espera si aumenta la concurrencia. Las conexiones persistentes pueden fallar tras un corte; no se agregan reintentos automáticos porque alterarían la carga. No se agrega caché de respuestas, por lo que no se introduce una política de invalidación o una frescura distinta.

Aceptar la candidata solo si la evidencia muestra un beneficio útil y consistente, con integridad correcta y sin costo inaceptable. Si no mejora o empeora, registrar el resultado y rechazarla; una conclusión honesta puede ser que la hipótesis no se sostuvo. El estado por defecto al iniciar es siempre baseline.

**Resultado, mejora/regresión, costo observado y decisión final: pendientes.** Completar `docs/conclusiones.md` citando las corridas reales.

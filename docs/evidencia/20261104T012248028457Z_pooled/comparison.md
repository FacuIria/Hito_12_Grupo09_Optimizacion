# Comparación real antes/después

Línea base: `20261104T011554960995Z_baseline`. Candidata: `20261104T012248028457Z_pooled`.

Mediana de las métricas de cada repetición durante sostenimiento; rango mínimo–máximo entre repeticiones.
Los percentiles no se promedian ni se presentan como un percentil conjunto.

| Métrica | Unidad | Baseline mediana [rango] | Pool mediana [rango] | Cambio % |
|---|---|---:|---:|---:|
| Latencia p50 | ms | 44.862 [39.912, 45.516] | 20.841 [20.818, 21.336] | -53.54 |
| Latencia p90 | ms | 52.352 [44.310, 52.575] | 23.106 [23.091, 24.307] | -55.86 |
| Latencia p95 | ms | 57.916 [50.890, 58.230] | 24.386 [24.346, 25.462] | -57.89 |
| Latencia p99 | ms | 64.515 [56.384, 67.611] | 26.745 [25.808, 30.599] | -58.54 |
| Latencia media | ms | 46.214 [41.056, 46.861] | 21.324 [21.169, 21.720] | -53.86 |
| Latencia exitosa p95 | ms | 57.916 [50.890, 58.230] | 24.386 [24.346, 25.462] | -57.89 |
| Latencia exitosa p99 | ms | 64.515 [56.384, 67.611] | 26.745 [25.808, 30.599] | -58.54 |
| API p95 | ms | 54.931 [48.512, 55.580] | 21.524 [21.423, 22.879] | -60.82 |
| Llamada al motor p95 | ms | 46.947 [40.076, 47.747] | 19.895 [19.368, 20.525] | -57.62 |
| Throughput exitoso | op/s | 8.000 [8.000, 8.000] | 8.000 [8.000, 8.000] | +0.00 |
| Operaciones completadas | operaciones | 240.000 [240.000, 240.000] | 240.000 [240.000, 240.000] | +0.00 |
| Operaciones exitosas | operaciones | 240.000 [240.000, 240.000] | 240.000 [240.000, 240.000] | +0.00 |
| Errores | operaciones | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | n/a (base cero) |
| Fracción de errores | fracción | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | n/a (base cero) |
| No enviadas | operaciones | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | n/a (base cero) |
| Atraso de despacho p95 | ms | 14.970 [14.966, 15.569] | 15.410 [15.268, 15.549] | +2.94 |
| Validación del cliente p95 | ms | 2.002 [1.677, 2.196] | 1.681 [1.666, 1.791] | -16.06 |

El signo negativo reduce la métrica; es favorable para latencia/errores y desfavorable para throughput.

## Recursos

Máximos observados en muestras discretas (todas las fases, no picos garantizados).

| Variante | Repetición | CPU host % | CPU API % | CPU motor % | RAM API % límite | RAM motor % límite | RAM generador MiB |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline | 1 | 11.2 | 19.8 | 16.7 | 11.0 | 5.9 | 47.9 |
| baseline | 2 | 30.2 | 23.0 | 18.1 | 11.0 | 5.8 | 51.8 |
| baseline | 3 | 25.7 | 22.7 | 18.2 | 11.0 | 5.9 | 52.5 |
| pooled | 1 | 10.8 | 3.1 | 16.6 | 7.3 | 6.5 | 48.0 |
| pooled | 2 | 12.1 | 2.9 | 17.1 | 7.4 | 6.6 | 51.4 |
| pooled | 3 | 11.4 | 3.1 | 16.3 | 7.4 | 6.4 | 52.8 |

## Límites de interpretación

- Menos de 1000 respuestas exitosas en alguna repetición: el 1% superior contiene menos de 10 observaciones; interpretar p99 con cautela. Este umbral es orientativo, no una garantía estadística.
- Tasa de llegada acotada: el throughput observado no demuestra capacidad máxima.
- Orden baseline→pooled; cachés del motor, carga externa y deriva térmica pueden influir.

## Decisión del equipo

A partir de los resultados obtenidos en las tres repeticiones realizadas sobre cada variante, el equipo decide **aceptar la optimización mediante reutilización de conexiones HTTP (`pooled`)** para el escenario de carga evaluado.

### Interpretación de los resultados

La optimización permitió reducir considerablemente los tiempos de respuesta respecto de la línea base.

La latencia p50 disminuyó de 44.862 ms a 20.841 ms, representando una reducción del 53,54 %. De manera similar, la latencia p95 se redujo un 57,89 % y la p99 un 58,54 %. La latencia media también presentó una mejora del 53,86 %.

Estos resultados respaldan la hipótesis técnica inicial, según la cual el tiempo destinado a la comunicación con InfluxDB representaba una oportunidad de optimización.

En particular, la latencia p95 de las llamadas al motor se redujo de 46.947 ms a 19.895 ms, equivalente a una mejora del 57,62 %. Esto es compatible con una reducción del costo asociado a la comunicación HTTP mediante la reutilización de conexiones.

Sin embargo, las mediciones no permiten atribuir de manera exclusiva toda la mejora al establecimiento de conexiones, ya que pueden intervenir otros factores del entorno.

### Throughput, errores e integridad

El throughput exitoso se mantuvo estable en 8 operaciones por segundo en ambas variantes, coincidiendo con la tasa objetivo configurada para el escenario.

En las tres repeticiones de cada variante se completaron exitosamente las 240 operaciones correspondientes al período de sostenimiento, sin registrar errores, solicitudes no enviadas ni interrupciones.

La comparación demuestra que la optimización permitió reducir los tiempos de respuesta sin afectar negativamente la cantidad de operaciones completadas bajo la carga evaluada.

Adicionalmente, la validación final realizada mediante el script `validar_integridad.ps1` confirmó la integridad de los 51.840 registros sintéticos utilizados en el laboratorio.

La evidencia quedó registrada en:

`docs/evidencia/20261104T012635878386Z_integridad/integrity.json`

### Consumo de recursos

También se observaron diferencias relevantes en el consumo de recursos.

Durante la línea base, la CPU máxima observada de la API alcanzó valores de entre 19,8 % y 23,0 %, mientras que en la variante optimizada se mantuvo entre 2,9 % y 3,1 %.

La memoria utilizada por la API también disminuyó, pasando de aproximadamente el 11 % al 7,4 % del límite asignado al contenedor.

Por su parte, InfluxDB mantuvo valores de CPU relativamente similares en ambas variantes, sin evidenciar saturación durante las pruebas. El consumo de memoria del motor fue ligeramente superior con la variante optimizada, pero permaneció dentro de los límites configurados.

Se observó una pequeña regresión en el atraso de despacho p95, que aumentó un 2,94 %. Esta variación no afectó la tasa objetivo alcanzada ni produjo errores, aunque deberá considerarse al evaluar escenarios con mayores niveles de concurrencia.

### Trade-offs de la optimización

Si bien la reutilización de conexiones HTTP produjo una mejora importante en los tiempos de respuesta, también introduce determinados costos y consideraciones técnicas.

El uso de un pool de conexiones implica administrar su configuración y ciclo de vida, establecer límites adecuados, controlar los tiempos de espera y contemplar mecanismos de recuperación ante conexiones inválidas o interrumpidas.

Asimismo, mantener conexiones disponibles puede implicar un consumo adicional de recursos y una mayor complejidad de mantenimiento respecto de una implementación que establece conexiones independientes.

Por lo tanto, la decisión de utilizar esta optimización debe considerar tanto la mejora observada como los costos operativos asociados.

### Limitaciones del experimento

Los resultados corresponden exclusivamente al escenario de carga reproducido en un entorno local, con un conjunto de 51.840 registros sintéticos y una tasa objetivo de 8 operaciones por segundo.

La prueba no permite establecer la capacidad máxima de procesamiento del sistema ni garantizar que las mejoras obtenidas se mantengan bajo condiciones de producción o mayores niveles de concurrencia.

Asimismo, los percentiles de latencia elevados, especialmente el p99, deben interpretarse con cautela debido a la cantidad de operaciones utilizadas en cada repetición.

También debe considerarse que la ejecución secuencial de la línea base y la variante optimizada puede estar influida por factores como el estado de las cachés, la carga externa del equipo y las condiciones del entorno.

Para futuras evaluaciones se recomienda ampliar el número de operaciones, incorporar escenarios de mayor concurrencia y realizar ejecuciones en distinto orden para reducir posibles sesgos experimentales.

### Conclusión final

A partir de las mediciones obtenidas, **el equipo acepta la optimización basada en reutilización de conexiones HTTP para el escenario evaluado**.

La variante optimizada logró reducir aproximadamente un 58 % la latencia p95 y p99, manteniendo el throughput objetivo y sin registrar errores durante las pruebas.

La validación posterior también confirmó la integridad de los 51.840 registros sintéticos utilizados.

En consecuencia, los resultados respaldan la decisión técnica adoptada, reconociendo sus trade-offs y las limitaciones propias del entorno experimental.

La optimización se considera favorable para el flujo analizado del Fixture Mundial 2030, sin extender esta conclusión a escenarios de mayor carga o entornos productivos que todavía no fueron evaluados.
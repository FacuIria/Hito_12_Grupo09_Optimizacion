# Conclusiones del Hito 12

## 1. Resumen de la evaluación

El Grupo 09 realizó una evaluación experimental de rendimiento sobre un flujo de consultas de estadísticas postpartido de la plataforma Fixture Mundial 2030.

El objetivo consistió en establecer una línea base reproducible, identificar una posible limitación de rendimiento, aplicar una optimización y comparar los resultados mediante mediciones reales.

Las pruebas se ejecutaron el 4 de noviembre de 2026 (UTC), en un entorno local Windows con Docker Desktop, Python 3.13.17, una API FastAPI e InfluxDB 3.12.2.

Se utilizó un conjunto de 51.840 registros sintéticos y se ejecutaron tres repeticiones de cada variante: línea base y optimización mediante reutilización de conexiones HTTP (`pooled`).

## 2. Preparación y ejecución

La preparación del conjunto de datos finalizó correctamente, generando 51.840 registros.

Se verificó la integridad inicial y se ejecutó una prueba de humo antes de iniciar las mediciones principales.

Posteriormente, se realizaron tres repeticiones de la línea base y tres repeticiones de la variante optimizada.

Durante cada repetición se programaron 319 operaciones, de las cuales 240 correspondieron a la fase de sostenimiento.

No se registraron errores de ejecución, operaciones no enviadas ni interrupciones.

Las evidencias quedaron almacenadas en:

- Preparación: `docs/evidencia/20261104T011338609443Z_preparacion/`
- Línea base: `docs/evidencia/20261104T011554960995Z_baseline/`
- Optimización: `docs/evidencia/20261104T012248028457Z_pooled/`
- Integridad final: `docs/evidencia/20261104T012635878386Z_integridad/`

## 3. Identificación del posible cuello de botella

El análisis de la línea base mostró que la mayor parte del tiempo registrado dentro de la API correspondía a la comunicación con la dependencia InfluxDB.

El tiempo medio de la llamada a la dependencia fue de aproximadamente 39,82 ms, frente a un tiempo medio de procesamiento de la API de aproximadamente 42,15 ms, considerando las tres repeticiones.

A partir de esta observación, se formuló la hipótesis de que la reutilización de conexiones HTTP permitiría reducir el costo asociado a la comunicación con InfluxDB.

Se decidió evaluar una variante que utiliza un pool de conexiones, manteniendo las condiciones del escenario de carga para posibilitar una comparación válida.

## 4. Resultados de rendimiento

Se compararon las medianas de las métricas obtenidas en las tres repeticiones de cada variante durante el período de sostenimiento.

| Métrica | Línea base | Optimización | Variación |
|---|---:|---:|---:|
| Latencia p50 | 44,862 ms | 20,841 ms | -53,54 % |
| Latencia p95 | 57,916 ms | 24,386 ms | -57,89 % |
| Latencia p99 | 64,515 ms | 26,745 ms | -58,54 % |
| Latencia media | 46,214 ms | 21,324 ms | -53,86 % |
| API p95 | 54,931 ms | 21,524 ms | -60,82 % |
| Dependencia p95 | 46,947 ms | 19,895 ms | -57,62 % |
| Throughput | 8 ops/s | 8 ops/s | 0 % |
| Errores | 0 | 0 | Sin cambios |

Los resultados muestran una reducción importante de los tiempos de respuesta de la variante optimizada.

La disminución de la latencia de las llamadas a InfluxDB respalda la hipótesis planteada sobre el costo de comunicación entre la API y la dependencia.

El throughput se mantuvo en 8 operaciones por segundo, coincidiendo con la tasa objetivo del escenario de prueba. Esto demuestra que ambas variantes pudieron sostener la carga configurada, pero no permite establecer la capacidad máxima del sistema.

## 5. Consumo de recursos

Se registraron métricas del equipo anfitrión, del generador de carga, de la API y del motor InfluxDB.

Durante la línea base, el consumo máximo de CPU observado en la API alcanzó el 23,0 %, mientras que en la variante optimizada el máximo registrado fue del 3,1 %.

El consumo de memoria de la API también disminuyó, pasando de aproximadamente el 11 % al 7,4 % del límite asignado.

InfluxDB mantuvo un consumo de CPU relativamente estable entre ambas variantes, aunque presentó un pequeño incremento en el porcentaje de memoria utilizada respecto de su límite.

Por otra parte, el atraso de despacho p95 aumentó un 2,94 %. Esta regresión debe conservarse en el análisis, aunque no produjo errores ni impidió alcanzar la tasa objetivo.

Los valores de recursos corresponden a máximos observados en muestras discretas y no representan necesariamente los picos absolutos.

## 6. Validación de integridad

La integridad de los datos se verificó antes y después de ejecutar las pruebas.

La validación final confirmó correctamente los 51.840 registros sintéticos, sin detectar alteraciones indebidas.

Asimismo, las seis repeticiones principales completaron las operaciones previstas sin registrar errores de integridad en las respuestas.

La evidencia final se encuentra en:

`docs/evidencia/20261104T012635878386Z_integridad/integrity.json`

Estos resultados permiten concluir que, bajo el escenario evaluado, la optimización no produjo pérdidas, duplicaciones ni alteraciones detectadas por las verificaciones implementadas.

## 7. Trade-offs de la optimización

La reutilización de conexiones HTTP permitió reducir considerablemente los tiempos de respuesta, pero introduce nuevos aspectos que deben administrarse.

El uso de un pool requiere configurar límites de conexiones, controlar su ciclo de vida, gestionar conexiones inválidas y contemplar mecanismos de recuperación ante fallas.

También puede incrementar la complejidad del mantenimiento y requerir recursos adicionales para conservar conexiones disponibles.

Por lo tanto, la optimización representa una decisión favorable para el escenario evaluado, pero sus beneficios deben analizarse junto con los costos operativos y de mantenimiento.

## 8. Integración con Data Mart

El proyecto contempla una propuesta de integración analítica orientada a responder preguntas relacionadas con las estadísticas del Fixture Mundial 2030.

El diseño se documenta en `docs/integracion_data_mart.md`, donde se describen las fuentes operacionales, los datos necesarios, las transformaciones y la estrategia de actualización.

La integración analítica busca evitar consultas repetitivas y costosas sobre las fuentes operacionales mediante una proyección destinada al análisis.

Esta propuesta corresponde a un diseño conceptual. No se implementó ni evaluó experimentalmente un Data Warehouse completo como parte de las pruebas de rendimiento realizadas.

## 9. Comparación con una alternativa relacional

La alternativa basada en una estructura relacional se analiza en `docs/comparacion_relacional.md`.

La comparación considera el patrón de acceso, la organización de las entidades, las relaciones entre tablas, las operaciones de consulta y las garantías de consistencia.

No se ejecutó un benchmark experimental equivalente contra una base de datos relacional.

Por esta razón, los resultados obtenidos no permiten afirmar que NoSQL sea superior a una solución relacional en términos generales.

La conveniencia de cada alternativa dependerá de los requisitos de acceso, el volumen de información, la concurrencia, las necesidades transaccionales y el tipo de análisis requerido.

## 10. Limitaciones de la evaluación

Las pruebas se realizaron en un entorno local y con un volumen de datos sintéticos inferior al que podría utilizar una plataforma productiva de mayor escala.

El escenario tuvo una tasa objetivo limitada a 8 operaciones por segundo, por lo que no permite establecer el rendimiento máximo ni la escalabilidad completa del sistema.

Los percentiles elevados, especialmente el p99, deben interpretarse con cautela debido al tamaño de la muestra.

También se reconoce que las pruebas se ejecutaron en el orden línea base y posteriormente variante optimizada. Las cachés, la carga externa del equipo y otros factores del entorno pueden influir en los resultados.

No se midió el rendimiento de una alternativa relacional ni de una implementación completa del Data Mart.

Para futuras evaluaciones se recomienda ampliar el volumen y la concurrencia, repetir las pruebas en distintos órdenes y analizar escenarios de mayor exigencia.

## 11. Decisión final del equipo

A partir de las mediciones obtenidas, el Grupo 09 decide **aceptar la optimización mediante reutilización de conexiones HTTP para el escenario evaluado**.

La variante optimizada redujo la latencia p95 un 57,89 % y la p99 un 58,54 %, manteniendo el throughput objetivo de 8 operaciones por segundo y sin registrar errores durante las pruebas.

La validación posterior también confirmó la integridad de los 51.840 registros sintéticos.

En consecuencia, se considera que la optimización aporta una mejora significativa al rendimiento del flujo seleccionado del Fixture Mundial 2030, dentro de las condiciones del laboratorio.

La conclusión queda limitada al escenario efectivamente evaluado y no constituye una garantía de rendimiento para ambientes productivos o cargas superiores.

El experimento demuestra la importancia de establecer una línea base reproducible, formular hipótesis técnicas, comparar mediciones equivalentes y verificar la integridad de los datos antes de adoptar decisiones de optimización.
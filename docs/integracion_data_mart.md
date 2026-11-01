# Propuesta de Data Mart

**Diseño conceptual, no ejecutado.** Pregunta: «¿Cómo evolucionan la posesión, los pases, los tiros y las recuperaciones por equipo durante cada partido, y cómo se comparan partidos y sedes sin releer continuamente la serie operacional?»

## Grano y procedencia

Hecho `hecho_equipo_partido_minuto`: un equipo de un partido en un intervalo UTC de un minuto, semiabierto `[inicio, fin)`. Clave natural `(partido_id, equipo_codigo, inicio_minuto_utc)`. La sede se obtiene del partido; si difiere entre fuentes se rechaza el enriquecimiento hasta resolver la inconsistencia.

| Columna o medida | Fuente | Transformación y carácter aditivo |
|---|---|---|
| Partido | Tag `partido_id` de InfluxDB | Correspondencia exacta con dimensión partido |
| Equipo | Tag `equipo_codigo` | En producción, correspondencia con código FIFA de MongoDB; AAA/BBB son sintéticos |
| Sede | `sede_id` de InfluxDB + catálogo de partidos | Validar correspondencia; no asumir igualdad entre etiquetas y nombres libres |
| Inicio de minuto | `time` UTC | Truncar al minuto; conservar zona y ventana |
| Suma de posesión y número de muestras | `posesion_pct` | Guardar suma/conteo; calcular media ponderada por muestras, no promedio de promedios |
| Pases acumulados al cierre | `pases_completados_total` | Última muestra por tiempo; no sumar acumulados entre minutos |
| Pases del minuto | Acumulado actual y anterior | Diferencia; reinicio/corrección se marca, no se convierte silenciosamente en cero |
| Tiros y recuperaciones | Campos `*_intervalo` | Suma de incrementos; aditiva por intervalos disjuntos |
| Calidad y linaje | Extracción/validación | Muestras esperadas/observadas, run_id, versión ETL, rango leído, instante de refresco |

Dimensiones: `dim_equipo` (código, nombre, confederación), `dim_partido` (ID, fecha, sede, participantes), `dim_sede` y `dim_tiempo`. Las fuentes adicionales son los módulos operacionales de equipos/partidos del Fixture; este laboratorio solo genera etiquetas de correspondencia, **no ejecuta** una integración con MongoDB/Neo4j/IRIS. Antes de implementarla se debe obtener y validar un catálogo de claves entre módulos, sin vincular por nombres ambiguos.

## ETL propuesto

1. Extraer las series del motor por partido y rango UTC. Leer una muestra anterior al rango para calcular diferencias de acumulados. Extraer los catálogos de equipos/partidos separadamente del camino de requests.
2. Escribir una zona temporal de staging identificada por `run_id`, `extracted_at`, versión y marca de avance. Validar tipos, rangos y clave natural antes de transformar.
3. Resolver dimensiones por códigos documentados. Una dimensión faltante queda en cuarentena o usa una clave «desconocida» explícita, sin descartar silenciosamente el hecho.
4. Agrupar por minuto, calcular suma/conteo de posesión, incrementos y último acumulado. Deduplicar la entrada por la clave operacional y política de revisión; registrar conflictos de valor.
5. Cargar mediante upsert por la clave natural en una transacción. Actualizar hechos y marca de avance solamente si se validan conteos y agregados. Una falla parcial revierte esa transacción; la extracción se puede repetir.
6. Publicar `refrescado_hasta_utc`, lag y métricas de calidad para que el consumidor conozca la frescura.

Frecuencia propuesta: cada minuto durante el partido y un reprocesamiento posterior al cierre. Objetivo de lag: hasta 2 minutos en condiciones normales; es un objetivo de diseño, **no un SLA medido**. Releer los últimos 5 minutos para absorber datos tardíos comunes. Si llegan datos más antiguos, registrar el rango afectado y ejecutar backfill del partido; una revisión final a las 24 horas cubre correcciones posteriores. Estos plazos son supuestos del diseño y deben acordarse con el consumidor.

Conservar watermark por fuente/partido; evitar avanzar todas las fuentes si solo una terminó. Un `run_id` completo determina qué versión se publica. Un retry no duplica hechos porque el upsert usa la misma clave. Si cambia un dato operacional tardío, reemplazar el agregado del intervalo y registrar la revisión, en vez de sumar de nuevo su aporte.

## Validaciones y trade-offs

Conciliar cantidad de filas leídas, rechazadas y deduplicadas; cantidad de intervalos esperados/publicados; sumas de tiros/recuperaciones por partido; suma/conteo de posesión; acumulado final y suma de incrementos bajo la política de resets. Alertar ante posesión fuera de 0–100, intervalos faltantes, dos sedes incompatibles o claves desconocidas. Mantener el detalle de rechazo y su causa.

La proyección evita recalcular una agregación de puntos crudos por cada consulta analítica. A cambio requiere almacenamiento adicional, ejecución ETL, mantenimiento de claves y aceptación de retraso. No reemplaza el endpoint operacional para consultas que exijan datos recién escritos. No se consulta una cadena de seis motores en cada request.

En producción, posesión con muestreo irregular requiere ponderación temporal o regularización explícita: suma/conteo simple solo es correcta bajo la distribución uniforme supuesta aquí. Los catálogos históricos pueden necesitar dimensiones con vigencia para conservar el contexto del partido; el diseño inicial debe documentar si opta por sobrescribir atributos o por mantener historia.

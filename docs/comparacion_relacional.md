# Comparación con una alternativa relacional

**Análisis conceptual. No se ejecutó un benchmark relacional y no se afirma superioridad de ninguna tecnología.** El patrón es consultar estadísticas de un partido, en un rango temporal, agrupadas por equipo, sede y ventana.

El [esquema y consulta de referencia](../config/alternativa_relacional.sql) propone PostgreSQL con `equipo`, `partido` y `estadistica_equipo`. La clave de la serie es `(partido_id, equipo_codigo, tiempo)`; la sede se normaliza en `partido`. El índice adicional `(partido_id, tiempo)` sirve al filtro por partido/rango con ambos equipos. Esa normalización supone que un partido tiene una sede estable; debe validarse frente al modelo operacional que incluye sede en sus tags.

| Aspecto | Flujo InfluxDB preparado | Alternativa relacional propuesta |
|---|---|---|
| Lectura | Filtro por partido/time, `date_bin`, agregados | Filtro e índice de rango, join con partido y agregados equivalentes |
| Escritura | Series con tags y timestamp; reescritura de misma clave | Inserción o upsert controlado por PK |
| Integridad referencial | Validación en preparación y consumo | PK, FK y CHECK; conflictos abortan según transacción |
| Atomicidad esperada | No se asume una transacción global entre motores | Transacción ACID para hechos/dimensiones de la misma base |
| Evolución analítica | Reagregar serie o mantener proyección | Consultar tablas, vistas materializadas o hechos de un Data Mart |
| Crecimiento | Más series/puntos, distribución temporal y selectividad importan | Más filas, índices, posible particionado temporal y costo de joins |
| Costo adicional | Catálogos externos y consistencia entre fuentes | Índices, escritura transaccional, vacuum/mantenimiento y refrescos |

InfluxDB puede ser conveniente si predomina la serie temporal con ingesta de puntos y consultas por tiempo, y el ecosistema del equipo ya utiliza ese motor. Un modelo relacional puede simplificar relaciones entre entidades y escrituras con garantías conjuntas. Ambos pueden mantener proyecciones analíticas; el uso de una no es exclusivo de NoSQL.

Una mayor concurrencia puede saturar CPU, conexiones, I/O o locks según consulta y motor. El índice propuesto no garantiza rendimiento y añade costo a inserciones. Tampoco el pool HTTP elimina una consulta costosa: ambas variantes SQL deben procesar los mismos datos.

La comparación experimental futura requeriría el mismo dataset, ventana y resultado, recursos equivalentes, índices y configuración declarados, versiones fijadas, calentamiento, tasa/agenda equivalentes, tres o más repeticiones y validación independiente. Separar el efecto del transporte HTTP de InfluxDB del protocolo del cliente relacional. No comparar una respuesta precalculada con una consulta cruda como si fueran el mismo trabajo.

**No medido:** latencia, throughput, almacenamiento, costo de índices/joins, ingestión y concurrencia de PostgreSQL. Los únicos resultados experimentales de esta entrega, cuando se ejecuten, serán baseline y pooled del mismo flujo FastAPI→InfluxDB.

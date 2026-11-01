# Auditoría de requisitos

Fuente: consigna oficial de 18 páginas. **Preparado** significa que existe implementación o diseño; **pendiente** indica la comprobación real que falta. Ningún requisito experimental se marca completo por haber escrito código o por pasar tests con dobles.

| ID | Cobertura preparada | Comprobación pendiente / evidencia final |
|---|---|---|
| RF1 | Flujo postpartido, endpoint, consumidor y fuentes en `flujo_y_escenario_de_carga.md` | Confirmar flujo desplegado en notebook |
| RF2 | `config/carga.json`, agenda, límites y fases en `hito12/load.py` | `plan.json`, operaciones emitidas y duración real |
| RF3 | Generador determinista, distribución y límites documentados | `preparation.json` e integridad de carga |
| RF4 | Baseline separado, commit/config/imágenes/versiones y recursos registrados | Ejecutar baseline antes de pooled |
| RF5 | Latencias/percentiles, throughput, errores, CPU/RAM e I/O | `load.json`, CSV y `resources.json` reales |
| RF6 | Cliente, API, llamada a dependencia, contenedores y host diferenciados | Verificar cobertura del muestreo; tiempo SQL puro no disponible |
| RF7 | Método de hipótesis y registro previo a candidata | Formular hipótesis con evidencia real de baseline |
| RF8 | Pool HTTP implementado como candidata | Activar después de RF7 y justificar con resultados |
| RF9 | Repetición de plan exacto y rechazo de condiciones distintas | Tres repeticiones por variante |
| RF10 | Comparador CSV/JSON/Markdown, recursos, errores y regresiones | Tablas reales y explicación |
| RF11 | Trade-offs del pool documentados | Relacionar con memoria/conexiones/costos observados |
| RF12 | Pregunta analítica y fuentes en `integracion_data_mart.md` | Diseño documentado; no se exige warehouse completo |
| RF13 | Staging, transformación, upsert, frecuencia, lag, tardíos y fallas | Propuesta documentada; ejecución ETL no realizada |
| RF14 | Modelo y SQL conceptual, garantías y conveniencia condicionada | Análisis documentado; benchmark relacional no realizado |
| RF15 | Oráculo por respuesta y hash completo antes/después | Resultados reales de integridad |
| RF16 | Estructura de evidencia inmutable por corrida | Preparación, base, candidata, comparación y conclusiones reales |
| RNF1 | README y scripts PowerShell con orden completo | Reproducción por otro integrante en notebook |
| RNF2 | Fecha/commit/config/dataset/duración/entorno registrados | Inspeccionar `experiment.json` reales |
| RNF3 | Controles de compatibilidad y documentación de diferencias | Par real válido; registrar ruido externo |
| RNF4 | Conteos, claves, hashes y registros sin confirmación | Evidencias reales de preparación/integridad |
| RNF5 | Unidades, método, muestras y límites explicados | Adjuntar CSV/JSON con número real de operaciones |
| RNF6 | Volumen local y proyección supuesta separados | Sustituir supuesto si el TPO define otra escala |
| RNF7 | Dataset sintético y recursos propios | Verificar aislamiento efectivo en notebook |
| RNF8 | Sin secretos, loopback, `.gitignore`, errores seguros | Revisar evidencia antes de publicarla |
| RNF9 | Límites Docker, preflight y parada por recursos | Comprobar límites y monitor en la máquina real |
| RNF10 | Separación app/herramientas/config/scripts/docs/datos/tests | Preparado y documentado |
| RNF11 | Preparación idempotente y limpieza por detención/reutilización | Comprobar repetición real sin pérdida |
| RNF12 | Tabla de procedencia y transformaciones del Data Mart | Diseño documentado; catálogos externos pendientes si se implementa |
| RNF13 | Estructura Git navegable y política de commits | Publicar código/evidencias/conclusiones en GitHub Hito 12 |
| RNF14 | Estados medido/objetivo/hipótesis/no ejecutado explícitos | Mantener esa distinción al cerrar el informe |

## Estado de entrega

- Código y documentación: preparados localmente.
- Pruebas locales del software: ver `verificacion_local.md`.
- Despliegue Docker, carga, rendimiento y validación de la base: pendientes en notebook.
- Conclusión sobre la candidata: pendiente de los resultados.
- Publicación de esta implementación y evidencia en GitHub: pendiente.

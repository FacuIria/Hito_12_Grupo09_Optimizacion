# Instrucciones permanentes de Codex — Hito 12 Grupo 09

## Alcance estricto

- **Trabajar únicamente en este repositorio:** `FacuIria/Hito_12_Grupo09_Optimizacion`.
- **Hito 11 es SOLO LECTURA:** `https://github.com/Agusmel03/Hito11_Grupo9_Conectividad`. No modificar allí código, documentación, ramas, commits, contenedores, servicios, configuración ni datos originales. No ejecutar cargas sobre el Hito 11. Si hace falta reproducir funcionalidad, construir una copia/variante propia y aislada de Hito 12.
- Leer `CONTEXTO_PARA_CODEX_HITO12.md` y la consigna oficial `Hito 12 — Requisitos Técnicos: Pruebas de Carga y Optimización.pdf` si están disponibles. El PDF oficial prevalece sobre cualquier síntesis.

## Seguridad y precisión

- No ejecutar pruebas pesadas ni operaciones potencialmente disruptivas sin comprobar el entorno y los límites de recursos. Preferir una carga progresiva y acotada.
- No detener, eliminar ni reiniciar los contenedores originales del Hito 11. No usar `docker compose down -v`, `docker volume rm`, `FLUSHALL`, borrado global, recreación destructiva o limpieza no restringida al dataset de Hito 12.
- No versionar secretos, tokens, contraseñas, variables privadas, URI autenticadas ni logs/capturas con valores sensibles.
- No afirmar que se ejecutó una prueba si no hay salida real. Separar **medido**, **estimado**, **hipótesis** y **no ejecutado**.
- Para cada prueba real guardar: fecha, commit, configuración no sensible, entorno/recursos, versiones, volumen, concurrencia, duración, operaciones totales, latencias/percentiles, throughput, errores y validación de integridad.
- Antes de optimizar, preservar la línea base. Después, repetir el mismo escenario y explicar cualquier desviación que afecte la comparación.

## Forma de trabajo

- Comunicarse en español y explicar las acciones de forma concisa.
- Inspeccionar el estado del repo y el entorno antes de modificar algo; no asumir que el repositorio aún está vacío.
- Generar código, scripts, README, docs y evidencias **solo en Hito 12**. Mantener una estructura clara, reproducible y compatible con Windows PowerShell cuando corresponda.
- Cubrir y auditar RF1–RF16 y RNF1–RNF14 de la consigna del Hito 12. No marcar requisitos como completos sin evidencia correspondiente.
- Distinguir la corrección pendiente de RF21 del Hito 11 de los requisitos del Hito 12. El comentario del docente sobre Redis implica una lección sobre pruebas reales, **no** autorización para tocar Hito 11.
- El Data Mart puede ser una propuesta de diseño/ETL documentada; no inventar ejecuciones ni implementar un warehouse completo sin necesidad.
- Antes de ejecutar comandos de red, instalar dependencias o hacer cambios en Docker, respetar los permisos del entorno de Codex y el aislamiento Hito 12.

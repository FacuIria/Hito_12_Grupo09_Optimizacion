# Evidencias

Todavía no hay evidencia de carga real con InfluxDB en esta carpeta. `verificacion_codigo.json` conserva la salida real de tests del software, identificada explícitamente como una verificación que no mide InfluxDB. Su explicación está en `docs/verificacion_local.md`.

`verificacion_macos.json` registra la auditoría posterior: 44 tests aprobados y controles locales, con el hash de la revisión modificada. Incluye un intento de arranque rechazado por memoria insuficiente; ese rechazo no es un resultado de carga. Se conserva la evidencia anterior de Windows sin sobrescribirla.

Las herramientas crearán carpetas con fecha UTC y sufijo:

```text
YYYYMMDDTHHMMSSffffffZ_preparacion/preparation.json
YYYYMMDDTHHMMSSffffffZ_integridad/integrity.json
YYYYMMDDTHHMMSSffffffZ_baseline/
  experiment.json
  trial_01/  (también 02 y 03)
    plan.json
    requests.csv
    resources.json
    load.json
    api_metrics.json
    integrity_before.json
    integrity_after.json
YYYYMMDDTHHMMSSffffffZ_pooled/
  hypothesis.json
  experiment.json
  trial_01/ ...
  comparison.md
  comparison.csv
  comparison.json
```

`requests.csv` contiene fase, secuencia, partido/resolución, instante programado, tipo de resultado, status HTTP, latencia, tiempos de API/dependencia/validación, retraso de despacho e ID de respuesta. No contiene cuerpos de respuesta ni datos de usuarios.

`resources.json` separa host, generador y contenedores. `load.json` conserva resúmenes, agenda, duración con drenaje y motivos de interrupción. `experiment.json` es el índice del experimento y su trazabilidad. Las filas `capacity`/`generator_late` son llegadas no enviadas, no errores HTTP ni éxitos.

Preparación: distinguir intentados, confirmados y sin confirmación. Integridad: distinguir cantidad esperada, real y hash completo. Comparación: solo generada si el par pasa controles de compatibilidad. No se rellenan archivos ficticios para ilustrar una mejora.

`preparation.json` incluye metadatos del código/entorno/versiones antes de escribir, fecha de cierre y tipo de fallo si la preparación se interrumpe. La preparación requiere un commit del código, igual que las mediciones.

Antes de entregar: conservar todas las repeticiones usadas, revisar metadatos, comprobar que no hay secretos, versionar las carpetas y enlazarlas desde las conclusiones y la matriz. Las capturas son opcionales: los CSV/JSON son la evidencia reproducible principal.

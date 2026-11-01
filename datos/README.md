# Generador de datos sintéticos

`python -m hito12.cli generate` produce `datos/generados/dataset.lp` y `manifest.json` sin conectarse a Docker ni escribir en una base. Configuración: `config/dataset.json`; implementación: `hito12/dataset.py`.

El manifiesto guarda conteos y SHA256 por partido, hash global y hashes de agregados calculados independientemente. El dataset predeterminado tiene 51.840 puntos, semilla 1209 y una ventana temporal fija. Cada partido tiene un generador pseudoaleatorio propio, por lo que el contenido de partidos existentes no depende de cuántos partidos se generen después.

Los archivos generados se excluyen de Git: se entregan el generador, configuración y evidencias pequeñas. No son datos extraídos de Hito 11. Ver `docs/flujo_y_escenario_de_carga.md` para distribución y límites.

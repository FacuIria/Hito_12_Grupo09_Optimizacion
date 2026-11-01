# Procedencia y alcance

La consigna oficial es la autoridad de requisitos: [PDF aportado](referencias/consigna_hito12.pdf), 18 páginas. El contexto de traspaso y `AGENTS.md` describen antecedentes y restricciones; no prueban resultados actuales.

Repositorio indicado por el usuario: [FacuIria/Hito11_Grupo9_Conectividad](https://github.com/FacuIria/Hito11_Grupo9_Conectividad), rama `main`, commit inspeccionado `772aeedf7e9f76a8eb17d18b35b21b34781f5a43`. Es un fork del repositorio de Agusmel03. Se fija esa revisión; no se presupone que incluya correcciones posteriores del original.

| Archivo de Hito 11 | Uso en Hito 12 |
|---|---|
| `api_hito11/app/adapters/influx3.py` | Copia del código en `app/upstream_influx3.py`, conservando consulta, agregaciones y conversión de respuesta |
| `api_hito11/app/schemas/models.py` | Subconjunto del contrato de estadísticas en `app/models.py` |
| `api_hito11/app/routes/api.py` | Ruta GET de estadísticas y parámetros validados |
| `api_hito11/app/services/fixture.py` | Forma de respuesta y corte a 1.000 filas, con indicador `truncado` |
| `api_hito11/requirements.txt` | Versiones directas de FastAPI, Pydantic, Uvicorn y HTTPX conservadas |

Fuente del adaptador: [archivo fijado por commit](https://github.com/FacuIria/Hito11_Grupo9_Conectividad/blob/772aeedf7e9f76a8eb17d18b35b21b34781f5a43/api_hito11/app/adapters/influx3.py).

## Diferencias declaradas

- Se despliega solo el flujo FastAPI→InfluxDB. No se levantan seis motores ni se consulta `/salud` de Hito 11.
- Datos nuevos, sintéticos y reproducibles, con códigos de equipo AAA/BBB. No se copian bases ni secretos.
- InfluxDB 3 Core **3.12.2**, versión fijada para este laboratorio. El diagnóstico histórico menciona 3.12.1; no se comparan mediciones entre esos entornos.
- Mismo SQL en baseline y pooled. La consulta conserva `AVG` de posesión, `MAX` del contador acumulado y `SUM` de eventos por intervalo.
- Se agregan identidad local, métricas y headers de tiempo a ambas variantes. El formato de error de dependencia se reduce a un mensaje seguro; no se pretende reproducir todas las respuestas de Hito 11.
- No hay autenticación en el laboratorio: solo puertos de loopback, red Docker interna y datos sintéticos. El marcador público `hito12-local-no-secret` mantiene el encabezado que enviaba el adaptador; no es una credencial.
- El modo `pooled` implementa una candidata, no una mejora acreditada. `baseline` sigue usando `httpx.get` por consulta.

No se ejecutó ningún comando sobre contenedores o datos de Hito 11. El pendiente RF21 de Hito 11 no forma parte de esta implementación ni se declara corregido.

## Referencias técnicas consultadas

- [Instalación y etiquetas de versión de InfluxDB 3](https://docs.influxdata.com/influxdb3/core/install/).
- [Configuración del servidor y límites de memoria](https://docs.influxdata.com/influxdb3/core/reference/config-options/).
- [Escritura v3: precisión, escrituras parciales y confirmación WAL](https://docs.influxdata.com/influxdb3/core/write-data/http-api/v3-write-lp/).
- [Dockerfile oficial de la imagen Core 3.12.2](https://github.com/influxdata/influxdata-docker/blob/master/influxdb/3.12-core/Dockerfile), inspeccionado para verificar usuario y directorio de persistencia.

Las opciones del despliegue están preparadas conforme a esas referencias; su ejecución en Docker queda pendiente. Las versiones observadas, IDs de imagen y recursos efectivos se registrarán en cada experimento.

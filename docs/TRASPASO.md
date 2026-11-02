# Traspaso para completar las pruebas

Se detuvo el trabajo experimental a pedido del equipo. No hay resultados de rendimiento ni mejora acreditada todavía.

## Estado real

- Suite de código: 47 tests aprobados antes del traspaso, con una advertencia Starlette/AnyIO. `evidencia/verificacion_perfil_compacto.json` corresponde al commit `da28d1a`, previo a la corrección de redes; los 47 tests volvieron a pasar después de esa corrección, con salida de consola, sin un nuevo JSON de verificación.
- Se construyó la imagen API y se iniciaron API e InfluxDB con el perfil compacto. Ambos procesos arrancaron, pero los puertos publicados quedaron vacíos con la red exclusivamente interna. No se pudo acceder desde el host.
- Se detuvieron únicamente los servicios Hito 12, conservando el volumen. No se cargó el dataset en InfluxDB ni se ejecutaron humo, baseline, candidata o comparación.
- Se añadió un bridge propio para acceso desde el host, conservando puertos loopback. La configuración y los tests se verificaron; **el arranque con esta corrección no se ha probado**.
- Hay dos perfiles: estándar y compacto. El compacto limita los contenedores a 960 MiB totales, genera 4.320 registros y ofrece 2 solicitudes/s. Ver `perfil_compacto.md`.
- En esta Mac quedaron contenedores Hito 12 detenidos con la configuración de red anterior. Esos contenedores/volumen no viajan con Git. Hito 11 no se modificó.

## En la máquina del compañero

1. Clonar/actualizar el repositorio y seguir los requisitos del README. No copiar `.venv`, `.runtime`, credenciales ni volúmenes de otra máquina.
2. Elegir un perfil antes de iniciar. En Windows con 8 GiB, seguir `perfil_compacto.md`; con recursos suficientes puede usarse el estándar del README. No mezclar perfiles ni bajar protecciones para forzar una corrida.
3. Ejecutar instalación/verificación y diagnóstico; comprobar RAM y disco. Iniciar servicios desde cero en esa máquina, preparar datos y validar integridad.
4. Ejecutar humo, después las tres repeticiones de baseline. Revisar los tiempos y recursos antes de formular la hipótesis.
5. Registrar hipótesis sustentada en los archivos reales y ejecutar las tres repeticiones de pooled con la misma configuración/dataset/imágenes/recursos.
6. Revisar comparación e integridad, completar `conclusiones.md` y `matriz_requisitos.md`. Guardar evidencias sin secretos y publicar los commits en el repositorio Hito 12.

Si se continúa en esta misma Mac, la red nueva requiere recrear únicamente los contenedores propios después de revisar recursos. `resume` no actualiza la configuración. No usar borrados de volúmenes; no se ensayó todavía ese paso. Las instrucciones de arranque desde cero se aplican a la máquina nueva.

Los escenarios estándar y extendido no se midieron. El diseño del Data Mart y la comparación relacional son conceptuales. No presentar tests con dobles como benchmark del motor ni completar métricas con estimaciones.

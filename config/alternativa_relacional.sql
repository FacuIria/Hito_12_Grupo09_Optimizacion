-- DISEÑO CONCEPTUAL PostgreSQL. No ejecutado ni usado para declarar rendimiento.
CREATE TABLE equipo (
    equipo_codigo char(3) PRIMARY KEY,
    nombre text NOT NULL
);
CREATE TABLE partido (
    partido_id varchar(10) PRIMARY KEY,
    sede_id text NOT NULL,
    inicio timestamptz NOT NULL
);
CREATE TABLE estadistica_equipo (
    partido_id varchar(10) NOT NULL REFERENCES partido,
    equipo_codigo char(3) NOT NULL REFERENCES equipo,
    tiempo timestamptz NOT NULL,
    posesion_pct double precision NOT NULL CHECK (posesion_pct BETWEEN 0 AND 100),
    pases_completados_total bigint NOT NULL CHECK (pases_completados_total >= 0),
    tiros_intervalo integer NOT NULL CHECK (tiros_intervalo >= 0),
    recuperaciones_intervalo integer NOT NULL CHECK (recuperaciones_intervalo >= 0),
    PRIMARY KEY (partido_id, equipo_codigo, tiempo)
);
-- Índice adicional para rangos de tiempo de ambos equipos del partido.
CREATE INDEX estadistica_partido_tiempo ON estadistica_equipo(partido_id, tiempo);

-- Parámetros enlazados por el cliente: partido, desde, hasta, intervalo permitido.
-- MAX del acumulado solo equivale al último cuando el contador es monótono.
SELECT date_bin($4::interval, e.tiempo, '1970-01-01T00:00:00Z'::timestamptz) AS tiempo,
       e.equipo_codigo, p.sede_id,
       AVG(e.posesion_pct) AS posesion_pct,
       MAX(e.pases_completados_total) AS pases_completados_total,
       SUM(e.tiros_intervalo) AS tiros_intervalo,
       SUM(e.recuperaciones_intervalo) AS recuperaciones_intervalo
FROM estadistica_equipo e
JOIN partido p USING (partido_id)
WHERE e.partido_id = $1 AND e.tiempo >= $2 AND e.tiempo < $3
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3
LIMIT 1001;

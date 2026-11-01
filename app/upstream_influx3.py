import httpx


class Influx3Adapter:
    def __init__(self, settings):
        self.settings = settings
        self.url = settings.influx_url.rstrip("/")
        self.database = settings.influx_database
        self.token = settings.influx_token.get_secret_value()
        self.timeout = settings.timeout_seconds

    def query_sql(self, sql):
        response = httpx.get(
            f"{self.url}/api/v3/query_sql",
            params={
                "db": self.database,
                "q": sql,
                "format": "json",
            },
            headers={
                "Authorization": f"Bearer {self.token}",
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def statistics(self, match_id, query):
        from datetime import timedelta

        minutos = {
            "1m": 1,
            "5m": 5,
            "15m": 15,
            "1h": 60,
        }[query.resolucion]

        inicio = query.desde.strftime("%Y-%m-%dT%H:%M:%SZ")
        fin = query.hasta.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Los identificadores de partido y equipo se validan
        # antes de llegar al adaptador.
        partido = match_id.replace("'", "''")

        filtro_equipo = ""
        if query.equipo:
            equipo = query.equipo.replace("'", "''")
            filtro_equipo = f"AND equipo_codigo = '{equipo}'"

        sql = f"""
        SELECT
            date_bin(
                INTERVAL '{minutos} minutes',
                time,
                TIMESTAMP '1970-01-01T00:00:00Z'
            ) AS tiempo,
            equipo_codigo,
            sede_id,
            AVG(posesion_pct) AS posesion_pct,
            MAX(pases_completados_total) AS pases_completados_total,
            SUM(tiros_intervalo) AS tiros_intervalo,
            SUM(recuperaciones_intervalo) AS recuperaciones_intervalo
        FROM estadisticas_equipo
        WHERE partido_id = '{partido}'
          AND time >= TIMESTAMP '{inicio}'
          AND time < TIMESTAMP '{fin}'
          {filtro_equipo}
        GROUP BY 1, 2, 3
        ORDER BY 1, 2, 3
        LIMIT 1001
        """

        filas = self.query_sql(sql)

        return [
            {
                "tiempo": fila["tiempo"] + "Z" if isinstance(fila["tiempo"], str) and not fila["tiempo"].endswith(("Z", "+00:00")) else fila["tiempo"],
                "equipo_codigo": fila["equipo_codigo"],
                "sede_id": fila["sede_id"],
                "posesion_pct": fila.get("posesion_pct"),
                "pases_completados_total": fila.get("pases_completados_total"),
                "tiros_intervalo": fila.get("tiros_intervalo"),
                "recuperaciones_intervalo": fila.get(
                    "recuperaciones_intervalo"
                ),
            }
            for fila in filas
        ]
    def ping(self):
        rows = self.query_sql(
            "SELECT COUNT(*) AS total FROM estadisticas_equipo"
        )
        if not isinstance(rows, list):
            raise ValueError("Respuesta SQL inesperada")
        return True

    def close(self):
        pass

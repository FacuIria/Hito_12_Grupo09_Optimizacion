import copy

import httpx
import pytest
from fastapi.testclient import TestClient

from app.adapter import MeasuredAdapter
from app.main import app
from app.models import StatsQuery

PARAMS = {'desde': '2030-06-08T19:00:00Z', 'hasta': '2030-06-08T20:30:00Z', 'resolucion': '5m'}


@pytest.mark.parametrize('mode', ['baseline', 'pooled'])
def test_original_sql_and_candidate_return_same_contract(monkeypatch, mode):
    queries = []
    def response(url, **kwargs):
        queries.append(kwargs['params']['q'])
        return httpx.Response(200, request=httpx.Request('GET', url), json=[{
            'tiempo': '2030-06-08T19:00:00', 'equipo_codigo': 'AAA', 'sede_id': 'S01',
            'posesion_pct': 50., 'pases_completados_total': 12, 'tiros_intervalo': 3,
            'recuperaciones_intervalo': 4}])
    adapter = MeasuredAdapter('http://influxdb:8181', mode)
    if mode == 'baseline':
        monkeypatch.setattr(httpx, 'get', response)
    else:
        monkeypatch.setattr(adapter.client, 'get', response)
    query = StatsQuery(**PARAMS)
    rows = adapter.statistics('P001', query)
    assert rows[0]['tiempo'] == '2030-06-08T19:00:00Z'
    assert 'LIMIT 1001' in queries[0]
    assert "partido_id = 'P001'" in queries[0]
    assert 'MAX(pases_completados_total)' in queries[0]
    assert adapter.timing.dependency_ms >= 0
    adapter.close()
    if mode == 'pooled':
        assert adapter.client.is_closed


def test_api_validates_input_before_dependency_and_reports_failures(monkeypatch):
    with TestClient(app) as client:
        def unavailable(*args):
            raise httpx.ConnectError('private diagnostic must not escape')
        monkeypatch.setattr(app.state.adapter, 'statistics', unavailable)
        assert client.get('/api/v1/partidos/P001/estadisticas', params=PARAMS).status_code == 503
        bad = copy.deepcopy(PARAMS)
        bad['hasta'] = '2030-06-10T20:30:00Z'
        assert client.get('/api/v1/partidos/P001/estadisticas', params=bad).status_code == 422
        bad = dict(PARAMS, equipo="AAA' OR 1=1")
        assert client.get('/api/v1/partidos/P001/estadisticas', params=bad).status_code == 422
        failure = client.get('/api/v1/partidos/P001/estadisticas', params=PARAMS)
        assert 'private diagnostic' not in failure.text
        assert failure.headers['X-Hito12-Lab'] == 'hito12-g09'


def test_utc_offset_window_and_invalid_naive_date():
    query = StatsQuery(desde='2030-06-08T16:00:00-03:00', hasta='2030-06-08T17:30:00-03:00')
    assert query.desde.hour == 19
    with pytest.raises(ValueError):
        StatsQuery(desde='2030-06-08T19:00:00', hasta=PARAMS['hasta'])

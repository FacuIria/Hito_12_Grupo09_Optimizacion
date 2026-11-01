import copy

from hito12.common import digest
from hito12.dataset import aggregate, canonical_rows, generate, rows_for_match, validate_response


def small_config():
    return {"schema_version": 1, "seed": 1209, "matches": 4, "minutes": 2,
            "step_seconds": 5, "start_utc": "2030-06-08T19:00:00Z",
            "database": "hito12_g09", "measurement": "estadisticas_equipo"}


def test_deterministic_dataset_and_unique_keys(tmp_path):
    cfg = small_config()
    one = generate(cfg, tmp_path / 'a')
    two = generate(cfg, tmp_path / 'b')
    assert one == two
    assert one['rows'] == 192
    assert (tmp_path / 'a/dataset.lp').read_bytes() == (tmp_path / 'b/dataset.lp').read_bytes()
    rows = list(rows_for_match(cfg, 1))
    assert len({(r['time'], r['partido_id'], r['equipo_codigo']) for r in rows}) == len(rows)
    for a, b in zip(rows[::2], rows[1::2]):
        assert round(a['posesion_pct'] + b['posesion_pct'], 2) == 100
    changed = dict(cfg, seed=1210)
    assert generate(changed, tmp_path / 'c')['raw_sha256'] != one['raw_sha256']


def test_independent_aggregate_known_values():
    rows = [dict(time=f'2030-06-08T19:00:{second:02d}Z', equipo_codigo='AAA', sede_id='S01',
                 posesion_pct=pos, pases_completados_total=passes, tiros_intervalo=shots,
                 recuperaciones_intervalo=recoveries)
            for second, pos, passes, shots, recoveries in [(0, 40, 2, 1, 3), (30, 60, 5, 2, 4)]]
    result = aggregate(rows, '1m')
    assert len(result) == 1
    assert result[0] == dict(tiempo='2030-06-08T19:00:00Z', equipo_codigo='AAA', sede_id='S01',
                             posesion_pct=50.0, pases_completados_total=5,
                             tiros_intervalo=3, recuperaciones_intervalo=7)


def test_http_200_is_insufficient_and_duplicates_are_detected(tmp_path):
    cfg = small_config()
    manifest = generate(cfg, tmp_path)
    case = {'match': 'P001', 'resolution': '1m'}
    body = {'data': {'partido_id': 'P001', 'resolucion': '1m', 'desde': manifest['from'],
                     'hasta': manifest['to'], 'truncado': False,
                     'items': aggregate(list(rows_for_match(cfg, 1)), '1m')}}
    assert validate_response(body, case, manifest)
    corrupted = copy.deepcopy(body)
    corrupted['data']['items'][0]['pases_completados_total'] += 1
    assert not validate_response(corrupted, case, manifest)
    corrupted = copy.deepcopy(body)
    corrupted['data']['items'].append(corrupted['data']['items'][0])
    assert not validate_response(corrupted, case, manifest)
    body['data']['items'] = []
    assert not validate_response(body, case, manifest)


def test_hash_tolerates_timestamp_serialization_not_data_corruption():
    rows = list(rows_for_match(small_config(), 1))
    same = copy.deepcopy(rows)
    same[0]['time'] = same[0]['time'].replace('Z', '.000000+00:00')
    assert digest(canonical_rows(rows, raw=True)) == digest(canonical_rows(same, raw=True))
    same[0]['time'] = same[0]['time'].replace('+00:00', '')
    assert digest(canonical_rows(rows, raw=True)) == digest(canonical_rows(same, raw=True))

import copy

import pytest
import yaml

from hito12.common import ROOT
from hito12.compare import compare, compatibility
from hito12.common import write_json
from hito12.dataset import generate, rows_for_match
from hito12.integrity import validate_source
from tests.test_dataset import small_config


def test_source_validator_detects_same_count_corruption(monkeypatch, tmp_path):
    cfg = small_config()
    manifest = generate(cfg, tmp_path)
    data = {f'P{i:03d}': list(rows_for_match(cfg, i)) for i in range(1, 5)}
    def fake_sql(client, query):
        if 'COUNT(*)' in query:
            return [{'total': manifest['rows']}]
        return copy.deepcopy(data[query.split("partido_id = '")[1].split("'")[0]])
    monkeypatch.setattr('hito12.integrity.sql', fake_sql)
    assert validate_source(None, manifest)['passed']
    data['P001'][0]['tiros_intervalo'] += 1
    assert not validate_source(None, manifest)['passed']


def experiment(mode):
    container = {'image_id': 'fixed', 'memory_limit': 1000, 'nano_cpus': 1000, 'id': 'engine-1'}
    return {'mode': mode, 'completed': True, 'config': {'repetitions': 1},
            'dataset_sha256': 'dataset', 'dataset_config': {}, 'dataset_records': 12,
            'metadata': {'source_sha256': 'code', 'machine_id_sha256': 'host', 'platform': 'Windows',
                         'python': '3.13', 'logical_cpus': 4, 'memory_total_bytes': 16000, 'docker': {},
                         'containers': {'api': copy.deepcopy(container), 'influxdb': copy.deepcopy(container)}},
            'trials': [{'completed': True, 'integrity_before': True, 'integrity_after': True,
                        'containers_stable': True, 'load': {'schedule_sha256': 'plan'}}]}


@pytest.mark.parametrize('change', ['dataset', 'source', 'image', 'hardware', 'integrity', 'plan', 'incomplete'])
def test_comparison_rejects_invalid_experiment(change):
    base, pooled = experiment('baseline'), experiment('pooled')
    assert compatibility(base, pooled) == []
    if change == 'dataset': pooled['dataset_sha256'] = 'other'
    if change == 'source': pooled['metadata']['source_sha256'] = 'other'
    if change == 'image': pooled['metadata']['containers']['api']['image_id'] = 'other'
    if change == 'hardware': pooled['metadata']['logical_cpus'] = 8
    if change == 'integrity': pooled['trials'][0]['integrity_after'] = False
    if change == 'plan': pooled['trials'][0]['load']['schedule_sha256'] = 'other'
    if change == 'incomplete': pooled['completed'] = False
    assert compatibility(base, pooled)


def test_compose_isolated_bounded_without_original_services():
    cfg = yaml.safe_load((ROOT / 'compose.yaml').read_text())
    assert cfg['name'] == 'hito12-g09'
    assert set(cfg['services']) == {'api', 'influxdb'}
    assert cfg['networks']['laboratorio']['internal'] is True
    for service in cfg['services'].values():
        assert service['mem_limit']
        assert float(service['cpus']) <= 2
        assert all(p.startswith('127.0.0.1:') for p in service['ports'])
        assert service['networks'] == ['laboratorio', 'acceso']
        assert service['labels']['edu.fixture.hito'] == '12'
    assert cfg['services']['influxdb']['volumes'] == ['datos_hito12:/var/lib/influxdb3']


def test_comparison_writes_tables_with_real_input_structure(tmp_path):
    """Valores inventados SOLO como fixture de test; nunca se publican como mediciones."""
    for mode in ('baseline', 'pooled'):
        exp = experiment(mode)
        exp['trials'][0]['number'] = 1
        value = 10. if mode == 'baseline' else 8.
        exp['trials'][0]['load']['steady'] = {
            'latency_ms': {'p50': value, 'p90': value, 'p95': value, 'p99': value, 'mean': value},
            'success_latency_ms': {'p95': value, 'p99': value},
            'api_ms': {'p95': value}, 'dependency_ms': {'p95': value},
            'throughput_success_per_second': 1., 'completed': 10, 'successful': 10, 'errors': 0,
            'error_fraction': 0., 'not_sent': 0, 'dispatch_lag_ms': {'p95': 1.},
            'validation_ms': {'p95': 1.}}
        write_json(tmp_path / mode / 'experiment.json', exp)
        sample = {'host_cpu_percent': 10., 'host_available_mb': 4096., 'generator_cpu_percent': 2.,
                  'generator_rss_mb': 50., 'containers': [{'Name': f'hito12-g09-{s}-1',
                    'CPUPerc': '5%', 'MemPerc': '10%'} for s in ('api', 'influxdb')]}
        write_json(tmp_path / mode / 'trial_01/resources.json', [sample])
    rows = compare(tmp_path / 'baseline', tmp_path / 'pooled')
    assert rows[0]['change_percent'] == pytest.approx(-20)
    assert (tmp_path / 'pooled/comparison.csv').is_file()
    assert 'Decisión del equipo' in (tmp_path / 'pooled/comparison.md').read_text(encoding='utf-8')
    assert 'Menos de 1000' in (tmp_path / 'pooled/comparison.md').read_text(encoding='utf-8')

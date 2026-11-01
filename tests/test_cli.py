"""Protecciones antes de mutar servicios y contabilidad de escrituras inciertas."""
import copy
from types import SimpleNamespace

import httpx
import pytest

from hito12 import cli
from hito12.common import ROOT, read_json
from tests.test_integrity_and_compare import experiment
from tests.test_dataset import small_config


@pytest.mark.parametrize('action', [cli.resume, cli.stop])
def test_lifecycle_refuses_unverified_containers_before_mutation(monkeypatch, action):
    monkeypatch.setattr(cli, 'resources', lambda *a, **k: None)
    monkeypatch.setattr(cli, 'local_docker', lambda: {})
    def refuse(**kwargs):
        assert kwargs == {'require_running': False}
        raise RuntimeError('Recurso ajeno')
    monkeypatch.setattr(cli, 'containers', refuse)
    monkeypatch.setattr(cli, 'compose', lambda *a, **k: pytest.fail('No debe mutar servicios'))
    with pytest.raises(RuntimeError, match='ajeno'):
        action(SimpleNamespace())


def test_pooled_rejects_environment_drift_before_changing_api(monkeypatch, tmp_path):
    cfg = read_json(ROOT / 'config/carga.json')
    base = experiment('baseline')
    base['config'] = cfg
    observed = copy.deepcopy(base['metadata'])
    observed['logical_cpus'] += 1
    evidence = tmp_path / 'load.json'
    evidence.write_text('{}')
    monkeypatch.setattr(cli, 'resources', lambda *a, **k: None)
    monkeypatch.setattr(cli, 'load_manifest', lambda: {'raw_sha256': 'dataset'})
    monkeypatch.setattr(cli, 'metadata', lambda: observed)
    monkeypatch.setattr(cli, 'resolve_baseline', lambda _: (tmp_path / 'experiment.json', base))
    monkeypatch.setattr(cli, 'compose', lambda *a, **k: pytest.fail('No debe cambiar la API'))
    args = SimpleNamespace(config='config/carga.json', mode='pooled', baseline=None,
                           hypothesis='Hipótesis de prueba basada en evidencia simulada', evidence=str(evidence))
    with pytest.raises(RuntimeError, match='logical_cpus'):
        cli.benchmark(args)


def test_write_timeout_is_unconfirmed_and_never_retried():
    calls = []
    def timeout(request):
        calls.append(request)
        raise httpx.ReadTimeout('Sin confirmación', request=request)
    report = {'attempted_records': 0, 'acknowledged_records': 0, 'failed_batch_records': 0}
    with httpx.Client(transport=httpx.MockTransport(timeout)) as client:
        with pytest.raises(httpx.ReadTimeout):
            cli.write_batch(client, ['point1\n', 'point2\n'], report)
    assert len(calls) == 1
    assert report['attempted_records'] == report['failed_batch_records'] == 2
    assert report['acknowledged_records'] == 0
    assert 'desconocida' in report['failure_note']


def test_preparation_failure_preserves_metadata_and_uncertain_batch(monkeypatch, tmp_path):
    from hito12.dataset import generate
    cfg = small_config()
    monkeypatch.setattr(cli, 'resources', lambda *a, **k: None)
    monkeypatch.setattr(cli, 'metadata', lambda: {'commit': 'test-commit', 'versions': {'fixture': True}})
    monkeypatch.setattr(cli, 'containers', lambda: {'influxdb': {'id': 'test-engine'}})
    monkeypatch.setattr(cli, 'config', lambda: cfg)
    monkeypatch.setattr(cli, 'RUNTIME', tmp_path / 'runtime')
    monkeypatch.setattr(cli, 'GENERATED', tmp_path / 'generated')
    monkeypatch.setattr(cli, 'generate', lambda _: generate(cfg, tmp_path / 'generated'))
    monkeypatch.setattr(cli, 'identity', lambda _: None)
    monkeypatch.setattr(cli, 'sql', lambda *a: [{'total': 0}])
    evidence = tmp_path / 'preparation'
    evidence.mkdir()
    monkeypatch.setattr(cli, 'new_directory', lambda _: evidence)
    def timeout(request):
        raise httpx.ReadTimeout('Fixture de fallo', request=request)
    monkeypatch.setattr(cli, 'client', lambda: httpx.Client(transport=httpx.MockTransport(timeout)))
    with pytest.raises(httpx.ReadTimeout):
        cli.prepare(SimpleNamespace())
    report = read_json(evidence / 'preparation.json')
    assert not report['completed']
    assert report['metadata']['commit'] == 'test-commit'
    assert report['failure_type'] == 'ReadTimeout'
    assert report['finished_utc'] >= report['date_utc']
    assert report['failed_batch_records'] == report['attempted_records'] > 0

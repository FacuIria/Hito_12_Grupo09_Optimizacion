import copy

import pytest

from hito12.common import ROOT, read_json
from hito12.load import distribution, schedule, summarize, validate_config


def test_plan_is_reproducible_and_ramp_respects_boundaries():
    cfg = read_json(ROOT / 'config/carga.json')
    manifest = {'counts': {f'P{i:03d}': 1 for i in range(1, 25)}}
    plan = schedule(cfg, manifest)
    assert plan == schedule(cfg, manifest)
    assert len([r for r in plan if r['phase'] == 'steady']) == 240
    assert all(5 < r['offset_s'] < 15 for r in plan if r['phase'] == 'ramp')
    assert all(15 <= r['offset_s'] < 45 for r in plan if r['phase'] == 'steady')
    assert len({r['sequence'] for r in plan}) == len(plan)


def test_latency_distribution_and_no_samples():
    assert distribution([1, 2, 3, 4, 5])['p95'] == pytest.approx(4.8)
    assert distribution([])['p99'] is None


def test_extended_plan_increases_samples_without_increasing_rate_or_concurrency():
    short = read_json(ROOT / 'config/carga.json')
    extended = read_json(ROOT / 'config/carga_extendida.json')
    assert extended['concurrency'] == short['concurrency'] == 4
    assert extended['rate_per_second'] == short['rate_per_second'] == 8
    plan = schedule(extended, {'counts': {f'P{i:03d}': 1 for i in range(1, 25)}})
    steady = [r for r in plan if r['phase'] == 'steady']
    assert len(steady) == 1200
    assert steady[-1]['offset_s'] < 165


def test_missing_arrivals_not_counted_as_success_and_warmup_excluded():
    cfg = read_json(ROOT / 'config/carga.json')
    row = {'phase': 'steady', 'kind': 'ok', 'latency_ms': 12., 'finished_s': 20.,
           'api_ms': 10., 'dependency_ms': 8., 'dispatch_lag_ms': 1., 'validation_ms': .2}
    rows = [row, dict(row, kind='capacity', latency_ms=None), dict(row, phase='warmup'),
            dict(row, kind='http_503'), dict(row, finished_s=46.)]
    result = summarize(rows, cfg)
    assert result['completed'] == 3
    assert result['successful'] == 2
    assert result['not_sent'] == 1
    assert result['errors'] == 1
    assert result['drained_successes'] == 1
    assert result['throughput_success_per_second'] == pytest.approx(1/30)


@pytest.mark.parametrize('key,value', [('concurrency', 999), ('rate_per_second', 5000),
                                     ('steady_seconds', -1), ('min_available_memory_mb', 0)])
def test_unsafe_config_rejected(key, value):
    cfg = read_json(ROOT / 'config/carga.json')
    cfg[key] = value
    with pytest.raises(ValueError):
        validate_config(cfg)

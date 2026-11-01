import json
import os
import subprocess
import sys
from types import SimpleNamespace

import pytest
import yaml

from hito12 import cli
from hito12.common import ROOT
from tests.test_integrity_and_compare import experiment
from hito12.compare import compatibility


def test_compact_configuration_is_isolated_and_bounded():
    env = dict(os.environ, HITO12_PROFILE='compacto')
    result = subprocess.run([sys.executable, '-c',
        'import json; from hito12.common import RUNTIME, GENERATED, VOLUME; '
        'from hito12.dataset import config; from hito12.profiles import LIMITS; '
        'print(json.dumps([str(RUNTIME),str(GENERATED),VOLUME,config(),LIMITS]))'],
        env=env, cwd=ROOT, capture_output=True, text=True, check=True)
    runtime, generated, volume, dataset, limits = json.loads(result.stdout)
    assert runtime.endswith('compacto') and generated.endswith('compacto')
    assert volume == 'hito12-g09_datos_hito12_compacto'
    assert dataset['matches'] * 2 * dataset['minutes'] * 60 / dataset['step_seconds'] == 4320
    compose = yaml.safe_load((ROOT / 'compose.compacto.yaml').read_text())
    assert compose['services']['influxdb']['mem_limit'] == '768m'
    assert compose['services']['api']['mem_limit'] == '192m'
    assert sum(v[0] for v in limits.values()) == 960 * 2**20
    assert compose['networks']['laboratorio']['internal'] is True
    assert all(p.startswith('127.0.0.1:') for s in compose['services'].values() for p in s['ports'])


def test_profiles_cannot_be_compared():
    base, pooled = experiment('baseline'), experiment('pooled')
    base['metadata']['profile'] = 'estandar'
    pooled['metadata']['profile'] = 'compacto'
    assert 'Entorno distinto: profile' in compatibility(base, pooled)


def test_resource_check_keeps_hard_reserve(monkeypatch):
    monkeypatch.setattr(cli.psutil, 'virtual_memory', lambda: SimpleNamespace(available=1500 * 2**20))
    monkeypatch.setattr(cli, 'local_docker', lambda: pytest.fail('Rechazar antes de consultar Docker'))
    with pytest.raises(RuntimeError, match='4096'):
        cli.resources({'min_available_memory_mb': 1024}, starting=True)

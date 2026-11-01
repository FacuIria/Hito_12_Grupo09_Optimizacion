. (Join-Path $PSScriptRoot 'common.ps1')
Invoke-Hito12 -Arguments @('run', '--mode', 'baseline', '--config', 'config/humo.json')

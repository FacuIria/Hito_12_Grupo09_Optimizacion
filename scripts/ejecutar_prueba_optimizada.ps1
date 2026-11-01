param([Parameter(Mandatory = $true)][string]$Hipotesis,
      [Parameter(Mandatory = $true)][string]$Evidencia,
      [string]$LineaBase = '')
. (Join-Path $PSScriptRoot 'common.ps1')
$runArgs = @('run', '--mode', 'pooled', '--config', 'config/carga.json',
             '--hypothesis', $Hipotesis, '--evidence', $Evidencia)
if ($LineaBase) { $runArgs += @('--baseline', $LineaBase) }
Invoke-Hito12 -Arguments $runArgs

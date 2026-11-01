param([ValidateSet('baseline', 'pooled')][string]$Modo = 'baseline',
      [string]$Configuracion = 'config/carga.json', [string]$LineaBase = '',
      [string]$Hipotesis = '', [string]$Evidencia = '')
. (Join-Path $PSScriptRoot 'common.ps1')
$runArgs = @('run', '--mode', $Modo, '--config', $Configuracion)
if ($LineaBase) { $runArgs += @('--baseline', $LineaBase) }
if ($Hipotesis) { $runArgs += @('--hypothesis', $Hipotesis) }
if ($Evidencia) { $runArgs += @('--evidence', $Evidencia) }
Invoke-Hito12 -Arguments $runArgs

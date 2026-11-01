param([Parameter(Mandatory = $true)][string]$LineaBase,
      [Parameter(Mandatory = $true)][string]$Optimizada)
. (Join-Path $PSScriptRoot 'common.ps1')
Invoke-Hito12 -Arguments @('compare', $LineaBase, $Optimizada)

# Politica elegida: reutilizar el dataset determinista, sin borrados.
# Detener libera CPU/RAM y conserva el volumen y toda la evidencia.
. (Join-Path $PSScriptRoot 'common.ps1')
Invoke-Hito12 -Arguments @('stop')

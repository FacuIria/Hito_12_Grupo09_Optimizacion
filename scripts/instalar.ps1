$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')
Push-Location $script:ProjectRoot
try {
    if (-not (Test-Path -LiteralPath $script:ProjectPython)) {
        py -3.13 -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Instalar Python 3.13 de 64 bits y volver a ejecutar.' }
    }
    & $script:ProjectPython -m pip install -r requirements-dev-lock.txt
    if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias.' }
    & $script:ProjectPython -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw 'Fallaron pruebas del codigo; no ejecutar carga.' }
}
finally { Pop-Location }
Invoke-Hito12 -Arguments @('doctor')

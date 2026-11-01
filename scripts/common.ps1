$ErrorActionPreference = 'Stop'
$script:ProjectRoot = Split-Path -Parent $PSScriptRoot
$script:ProjectPython = Join-Path $script:ProjectRoot '.venv\Scripts\python.exe'

function Invoke-Hito12 {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    if (-not (Test-Path -LiteralPath $script:ProjectPython)) {
        throw 'Primero ejecutar .\scripts\instalar.ps1'
    }
    Push-Location $script:ProjectRoot
    try {
        & $script:ProjectPython -m hito12.cli @Arguments
        if ($LASTEXITCODE -ne 0) { throw "Hito 12 termino con codigo $LASTEXITCODE. Revisar el mensaje anterior." }
    }
    finally { Pop-Location }
}

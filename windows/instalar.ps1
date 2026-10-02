$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 -m venv .venv
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python -m venv .venv
} else {
    throw 'Instale Python 3.11 ou superior de python.org, habilite PATH e reabra o PowerShell.'
}
if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar ambiente Python.' }
$Python = Join-Path (Get-Location) '.venv\Scripts\python.exe'
& $Python -c "import sys; assert sys.version_info >= (3,11), 'Python 3.11 ou superior necessario'"
if ($LASTEXITCODE -ne 0) { throw 'Versao de Python nao suportada.' }
& $Python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar dependencias. Verifique a internet.' }
if (-not (Test-Path '.env')) { Copy-Item '.env.example' '.env' }
Write-Host 'Instalacao concluida. Preencha .env localmente. Nunca compartilhe esse arquivo.'
Write-Host 'Depois execute: .\.venv\Scripts\python.exe -m src.main --check'

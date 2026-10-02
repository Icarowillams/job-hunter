param([switch]$SemEmail, [switch]$AbrirRelatorio)
$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root
$Python = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path $Python)) { throw 'Execute windows\instalar.ps1 primeiro.' }
New-Item -ItemType Directory -Force -Path 'logs' | Out-Null
# Mutex por caminho impede sobreposicao entre execucoes manuais e agendadas.
$Hash = [System.Security.Cryptography.SHA256]::Create()
$Key = ([BitConverter]::ToString($Hash.ComputeHash([Text.Encoding]::UTF8.GetBytes($Root)))).Replace('-','')
$Mutex = New-Object System.Threading.Mutex($false, "Local\JobHunter_$Key")
$Acquired = $false
try {
    try { $Acquired = $Mutex.WaitOne(0) } catch [System.Threading.AbandonedMutexException] { $Acquired = $true }
    if (-not $Acquired) { Write-Host 'Ja existe uma execucao em andamento.'; exit 0 }
    $Arguments = @('-m', 'src.main')
    if ($SemEmail) { $Arguments += '--dry-run' }
    if ($AbrirRelatorio) { $Arguments += '--open-report' }
    $Log = Join-Path $Root ('logs\execucao-' + (Get-Date -Format 'yyyy-MM-dd-HHmmss') + '.log')
    & $Python @Arguments 2>&1 | Tee-Object -FilePath $Log
    $Code = $LASTEXITCODE
    # Preserva os 30 logs mais recentes.
    Get-ChildItem 'logs\execucao-*.log' | Sort-Object LastWriteTime -Descending | Select-Object -Skip 30 | Remove-Item
    exit $Code
} finally {
    if ($Acquired) { $Mutex.ReleaseMutex() }
    $Mutex.Dispose()
}

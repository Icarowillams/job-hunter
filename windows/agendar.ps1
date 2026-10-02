param([string]$Horario = '07:00', [switch]$Remover)
$ErrorActionPreference = 'Stop'
$Name = 'Job Hunter Pessoal'
if ($Remover) {
    Unregister-ScheduledTask -TaskName $Name -Confirm:$false
    Write-Host 'Agendamento removido.'
    exit 0
}
$Root = Split-Path $PSScriptRoot -Parent
$Run = Join-Path $PSScriptRoot 'executar.ps1'
$Python = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path $Python)) { throw 'Execute instalar.ps1 primeiro.' }
$At = [datetime]::ParseExact($Horario, 'HH:mm', [System.Globalization.CultureInfo]::InvariantCulture)
$Action = New-ScheduledTaskAction -Execute $Python -Argument '-m src.scheduled' -WorkingDirectory $Root
$Trigger = New-ScheduledTaskTrigger -Daily -At $At
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 20) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$User = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$Principal = New-ScheduledTaskPrincipal -UserId $User -LogonType Interactive -RunLevel Limited
$Task = New-ScheduledTask -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Description 'Busca pessoal de vagas; depende de usuario logado, internet e notebook acordado.'
Register-ScheduledTask -TaskName $Name -InputObject $Task -Force | Out-Null
Write-Host "Agendado diariamente as $Horario no horario local do notebook."
Write-Host 'Requer usuario logado. Execucao perdida pode ocorrer ao retornar, conforme Windows. Nao acorda notebook desligado.'

param(
  [int]$IntervalMinutes = 90,
  [string]$TaskName = 'Union-Dev-AutoTick'
)

$ErrorActionPreference = 'Stop'
$script = 'D:\SynologyDrive\project\Union\ops\automation\union-dev-tick.ps1'
$goose = (Get-Command goose -ErrorAction Stop).Source
if (-not (Test-Path -LiteralPath $script)) { throw "missing $script" }

$action = New-ScheduledTaskAction -Execute 'powershell.exe' `
  -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$script`" -GoosePath `"$goose`"" `
  -WorkingDirectory 'D:\SynologyDrive\project\Union'

$trigger = New-ScheduledTaskTrigger -AtLogOn
$trigger.Repetition = (New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) `
  -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) `
  -RepetitionDuration (New-TimeSpan -Days 365)).Repetition

$settings = New-ScheduledTaskSettingsSet `
  -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
  -StartWhenAvailable -MultipleInstances IgnoreNew `
  -ExecutionTimeLimit (New-TimeSpan -Hours 4)

$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal `
  -Description 'UNION V1 autonomous slice tick: advance one card per run and keep the online Kanban in sync.' -Force | Out-Null

Get-ScheduledTask -TaskName $TaskName | Select-Object TaskName, State | Format-List
(Get-ScheduledTask -TaskName $TaskName).Triggers | Select-Object StartBoundary, Repetition | Format-List

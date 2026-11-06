param(
  [int]$MaxTurns = 70,
  [switch]$DryRun,
  [string]$GoosePath = 'goose'
)

$ErrorActionPreference = 'Stop'
$root = 'D:\SynologyDrive\project\Union'
$stateDir = Join-Path $env:LOCALAPPDATA 'union-autodev'
$logDir = Join-Path $stateDir 'logs'
$backupRoot = Join-Path $stateDir 'backups'
New-Item -ItemType Directory -Force -Path $logDir, $backupRoot | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$log = Join-Path $logDir "tick-$stamp.log"

function Write-Log([string]$message) {
  $line = "[$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss'))] $message"
  Add-Content -LiteralPath $log -Value $line -Encoding UTF8
  Write-Output $line
}

$lock = Join-Path $stateDir 'tick.lock'
if (Test-Path -LiteralPath $lock) {
  $age = (Get-Date) - (Get-Item -LiteralPath $lock).LastWriteTime
  if ($age.TotalHours -lt 4) {
    Write-Log "SKIP another tick is running (lock age $([int]$age.TotalMinutes) min)"
    exit 0
  }
  Write-Log "stale lock removed (age $([int]$age.TotalHours) h)"
  Remove-Item -LiteralPath $lock -Force
}
New-Item -ItemType File -Path $lock -Force | Out-Null

try {
  Set-Location $root
  Write-Log "tick start (dryrun=$($DryRun.IsPresent), maxTurns=$MaxTurns)"

  # --- host-local credentials & proxy (never stored in the repo) ---
  $envFile = Join-Path $env:USERPROFILE '.union-kanban.env'
  if (-not (Test-Path -LiteralPath $envFile)) { Write-Log 'FAIL .union-kanban.env missing'; exit 1 }
  foreach ($line in Get-Content -LiteralPath $envFile -Encoding UTF8) {
    if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+?)\s*$') {
      [Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process')
    }
  }
  $env:NODE_OPTIONS = '--use-env-proxy'

  # --- keep the checkout on the delivered upstream commit ---
  & git fetch origin --prune 2>&1 | Out-Null
  $behind = [int](& git rev-list --count 'HEAD..origin/rewrite/charter-v1')
  $dirty = @(& git status --porcelain -uall | Where-Object { $_ -notmatch '_Conflict' -and $_ -notmatch 'ops/automation/state' })
  Write-Log "git: behind=$behind dirty=$($dirty.Count)"
  if ($behind -gt 0) {
    if ($dirty.Count -eq 0) {
      & git merge --ff-only origin/rewrite/charter-v1 2>&1 | Out-Null
      Write-Log "git: fast-forwarded to $(git rev-parse --short HEAD)"
    } else {
      Write-Log 'git: worktree dirty, skipping fast-forward (resolve manually)'
    }
  }

  # --- ledger integrity gate ---
  $check = & node scripts/project-management.mjs check 2>&1
  if ($LASTEXITCODE -ne 0) {
    Write-Log "FAIL ledger check: $($check -join ' ')"
    exit 1
  }
  Write-Log "ledger check: PASS"

  # --- select the next eligible V1 card from the online board ---
  $selectionJson = & node ops/automation/pick-next.mjs 2>&1
  Set-Content -LiteralPath (Join-Path $stateDir 'selection.json') -Value ($selectionJson -join "`n") -Encoding UTF8
  try { $sel = $selectionJson | ConvertFrom-Json } catch { Write-Log "FAIL board selection unreadable: $($selectionJson -join ' ')"; exit 1 }
  if ($sel.reason) { Write-Log "FAIL board selection: $($sel.reason)"; exit 1 }
  Write-Log "board rev=$($sel.revision) in_flight=$($sel.in_flight) ready=$(@($sel.ready).Count) done=$(@($sel.done).Count)"

  if ($sel.all_v1_done) {
    Set-Content -LiteralPath (Join-Path $stateDir 'ALL_V1_DONE') -Value "all V1 cards done at $((Get-Date).ToString('s'))" -Encoding UTF8
    Write-Log 'ALL V1 TASKS DONE - nothing left to advance'
    exit 0
  }
  if (-not $sel.next) {
    Write-Log "no actionable card (in_flight=$($sel.in_flight)/$($sel.wip_limit))"
    exit 0
  }

  $task = $sel.next.id
  $card = $sel.next.card
  $actor = "goose/auto-tick/$env:COMPUTERNAME"
  Write-Log "selected $task card=$card version=$($sel.next.version) actor=$actor"

  if ($DryRun) { Write-Log "DRY RUN - would invoke goose for $task"; exit 0 }

  # --- one bounded slice step ---
  $gooseArgs = @(
    'run', '--recipe', 'ops/automation/union-slice-tick.yaml', '--no-session',
    '--max-turns', "$MaxTurns",
    '--params', "u_task=$task",
    '--params', "card_id=$card",
    '--params', "actor=$actor"
  )
  $outFile = Join-Path $logDir "goose-$stamp.out.log"
  $errFile = Join-Path $logDir "goose-$stamp.err.log"
  Write-Log "invoking goose ($GoosePath) -> $outFile"
  $proc = Start-Process -FilePath $GoosePath -ArgumentList $gooseArgs -WorkingDirectory $root `
    -RedirectStandardOutput $outFile -RedirectStandardError $errFile -PassThru -Wait -WindowStyle Hidden
  $gooseExit = $proc.ExitCode
  $gooseOutput = @()
  if (Test-Path -LiteralPath $outFile) { $gooseOutput += Get-Content -LiteralPath $outFile -Encoding UTF8 }
  if (Test-Path -LiteralPath $errFile) {
    $errTail = Get-Content -LiteralPath $errFile -Encoding UTF8 -Tail 20
    if ($errTail) { Add-Content -LiteralPath $log -Value ("stderr tail:" + "`n" + ($errTail -join "`n")) -Encoding UTF8 }
  }
  if ($gooseOutput) { Add-Content -LiteralPath $log -Value ($gooseOutput -join "`n") -Encoding UTF8 }
  $resultLine = ($gooseOutput | Where-Object { $_ -match 'TICK_RESULT:' } | Select-Object -Last 1)
  Write-Log "goose exit=$gooseExit result=$resultLine"

  # --- post-tick board sync verification ---
  $after = & node ops/automation/pick-next.mjs 2>&1
  try {
    $afterSel = $after | ConvertFrom-Json
    $cardAfter = @($afterSel.done + @($afterSel.ready | ForEach-Object { $_.id }) + @($afterSel.blocked | ForEach-Object { $_.id })) -contains $task
    Write-Log "post-tick board rev=$($afterSel.revision) in_flight=$($afterSel.in_flight) task_known=$cardAfter"
  } catch {
    Write-Log "post-tick board read unreadable"
  }

  if ($resultLine -match 'TICK_RESULT:\s*(\S+)\s+(\S+)\s+(\S+)') {
    Write-Log "tick outcome: task=$($matches[1]) status=$($matches[2]) sha=$($matches[3])"
  }
  exit 0
}
finally {
  Remove-Item -LiteralPath $lock -Force -ErrorAction SilentlyContinue
}

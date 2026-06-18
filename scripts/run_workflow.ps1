param(
    [ValidateSet("daily", "daily-ops", "weekly", "portfolio-check", "notification-summary", "notification-plan", "notification-packets", "daily-health", "weekly-health", "operations-status", "go-live-check", "decision-sheet", "mobile-summary", "line-check", "line-summary", "replay-quick", "replay", "backtest")]
    [string]$Command = "daily",
    [switch]$Refresh
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Tmp = Join-Path $ProjectRoot "tmp"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python virtual environment not found: $Python"
}

if (-not (Test-Path -LiteralPath $Tmp)) {
    New-Item -ItemType Directory -Path $Tmp | Out-Null
}

$env:TMP = $Tmp
$env:TEMP = $Tmp

$Arguments = @("-m", "src.main", $Command)
if ($Refresh) {
    $Arguments += "--refresh"
}

Push-Location $ProjectRoot
try {
    & $Python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Workflow failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}

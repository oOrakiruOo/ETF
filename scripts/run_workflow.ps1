param(
    [ValidateSet("daily", "daily-ops", "weekly", "weekly-line-summary", "user-friction-sim", "self-check", "line-self-check-reply", "portfolio-check", "notification-summary", "notification-plan", "notification-packets", "daily-health", "weekly-health", "operations-status", "go-live-check", "decision-sheet", "mobile-summary", "decision-brief", "line-check", "line-test", "line-broadcast-test", "line-summary", "line-broadcast-summary", "line-decision-brief", "line-broadcast-decision-brief", "line-broadcast-weekly-summary", "replay-quick", "replay", "backtest")]
    [string]$Command = "daily",
    [switch]$Refresh,
    [string]$Status = "kept",
    [string]$Reason = "",
    [string]$Text = ""
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
$LineToken = [Environment]::GetEnvironmentVariable("LINE_CHANNEL_ACCESS_TOKEN", "User")
$LineToUserId = [Environment]::GetEnvironmentVariable("LINE_TO_USER_ID", "User")
if ($LineToken) {
    $env:LINE_CHANNEL_ACCESS_TOKEN = $LineToken
}
if ($LineToUserId) {
    $env:LINE_TO_USER_ID = $LineToUserId
}

$Arguments = @("-m", "src.main", $Command)
if ($Refresh) {
    $Arguments += "--refresh"
}
if ($Command -eq "self-check") {
    $Arguments += @("--status", $Status)
    if ($Reason) {
        $Arguments += @("--reason", $Reason)
    }
}
if ($Command -eq "line-self-check-reply") {
    $Arguments += @("--text", $Text)
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

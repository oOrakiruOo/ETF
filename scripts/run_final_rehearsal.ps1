param(
    [switch]$Refresh,
    [switch]$SendLine,
    [switch]$UsePush
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Runner = Join-Path $ProjectRoot "scripts\run_workflow.ps1"

$DailyOpsArgs = @("-File", $Runner, "-Command", "daily-ops")
if ($Refresh) {
    $DailyOpsArgs += "-Refresh"
}

Write-Host "1/5 daily-ops"
& powershell.exe -NoProfile -ExecutionPolicy Bypass @DailyOpsArgs

Write-Host "2/5 daily-health"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Runner -Command daily-health

Write-Host "3/5 operations-status"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Runner -Command operations-status

Write-Host "4/5 line-check"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Runner -Command line-check

Write-Host "5/5 go-live-check"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Runner -Command go-live-check

if ($SendLine) {
    $LineCommand = if ($UsePush) { "line-decision-brief" } else { "line-broadcast-decision-brief" }
    Write-Host "LINE send: $LineCommand"
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Runner -Command $LineCommand
}

Write-Host "Final rehearsal completed. Check reports/daily/go_live_readiness_YYYY-MM-DD.md."

param(
    [switch]$Refresh
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Runner = Join-Path $ProjectRoot "scripts\run_workflow.ps1"

$DailyOpsArgs = @("-File", $Runner, "-Command", "daily-ops")
if ($Refresh) {
    $DailyOpsArgs += "-Refresh"
}

Write-Host "1/3 daily-ops"
& powershell.exe -NoProfile -ExecutionPolicy Bypass @DailyOpsArgs

Write-Host "2/3 line-check"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Runner -Command line-check

Write-Host "3/3 go-live-check"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Runner -Command go-live-check

Write-Host "Final rehearsal completed. Check reports/daily/go_live_readiness_YYYY-MM-DD.md."

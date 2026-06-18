$ErrorActionPreference = "Stop"
$OutputEncoding = [Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [Text.UTF8Encoding]::new()

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$DailyDir = Join-Path $ProjectRoot "reports\daily"

function Get-LatestFile($Pattern) {
    Get-ChildItem -Path $DailyDir -Filter $Pattern -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime |
        Select-Object -Last 1
}

$MobileSummary = Get-LatestFile "mobile_summary_*.txt"
$GoLive = Get-LatestFile "go_live_readiness_*.md"
$DailyHealth = Get-LatestFile "daily_health_*.md"

Write-Host "Latest ETF Rotation Status"
Write-Host ""

if ($MobileSummary) {
    Write-Host "[mobile-summary] $($MobileSummary.FullName)"
    Get-Content -Path $MobileSummary.FullName -Encoding UTF8 -TotalCount 12
}
else {
    Write-Host "[mobile-summary] missing"
}

Write-Host ""
if ($GoLive) {
    Write-Host "[go-live] $($GoLive.FullName)"
    Select-String -Path $GoLive.FullName -Encoding UTF8 -Pattern "GO|HOLD|Block|Review|LINE" | Select-Object -First 12
}
else {
    Write-Host "[go-live] missing"
}

Write-Host ""
if ($DailyHealth) {
    Write-Host "[daily-health] $($DailyHealth.FullName)"
}
else {
    Write-Host "[daily-health] missing"
}

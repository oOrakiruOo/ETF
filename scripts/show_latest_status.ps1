$ErrorActionPreference = "Stop"
$OutputEncoding = [Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [Text.UTF8Encoding]::new()

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$DailyDir = Join-Path $ProjectRoot "reports\daily"
$LineDir = Join-Path $ProjectRoot "data\processed\line"

function Get-LatestFile($Pattern) {
    Get-ChildItem -Path $DailyDir -Filter $Pattern -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime |
        Select-Object -Last 1
}

$MobileSummary = Get-LatestFile "mobile_summary_*.txt"
$DecisionBrief = Get-LatestFile "decision_brief_*.txt"
$GoLive = Get-LatestFile "go_live_readiness_*.md"
$DailyHealth = Get-LatestFile "daily_health_*.md"
$LineDeliveryLog = if (Test-Path $LineDir) {
    Get-ChildItem -Path $LineDir -Filter "line_delivery_log_*.csv" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime |
        Select-Object -Last 1
}
$LineTaskName = "MASATO ETF Rotation LINE Summary"

Write-Host "Latest ETF Rotation Status"
Write-Host ""

if ($DecisionBrief) {
    Write-Host "[decision-brief] $($DecisionBrief.FullName)"
    Get-Content -Path $DecisionBrief.FullName -Encoding UTF8 -TotalCount 28
}
else {
    Write-Host "[decision-brief] missing"
}

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

Write-Host ""
Write-Host "[line-task] $LineTaskName"
$LineTask = schtasks /Query /TN $LineTaskName /V /FO LIST 2>$null
if ($LASTEXITCODE -eq 0) {
    $LineTask |
        Select-String -Pattern "Next Run Time|Status|Last Run Time|Last Result|Task To Run" |
        ForEach-Object { Write-Host $_.Line }
}
else {
    Write-Host "missing"
}

Write-Host ""
if ($LineDeliveryLog) {
    Write-Host "[line-delivery] $($LineDeliveryLog.FullName)"
    Import-Csv -Path $LineDeliveryLog.FullName -Encoding UTF8 |
        Select-Object -Last 3 |
        Format-Table -AutoSize
}
else {
    Write-Host "[line-delivery] missing"
}

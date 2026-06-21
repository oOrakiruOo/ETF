$ErrorActionPreference = "Stop"
$OutputEncoding = [Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [Text.UTF8Encoding]::new()

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$LineDir = Join-Path $ProjectRoot "data\processed\line"
$TaskName = "MASATO ETF Rotation LINE Summary"

Write-Host "ETF Rotation LINE Delivery Check"
Write-Host ""

Write-Host "[task]"
$Task = schtasks /Query /TN $TaskName /V /FO LIST 2>$null
if ($LASTEXITCODE -eq 0) {
    $Task |
        Select-String -Pattern "Next Run Time|Status|Last Run Time|Last Result|Task To Run" |
        ForEach-Object { Write-Host $_.Line }
}
else {
    Write-Host "missing"
}

Write-Host ""
Write-Host "[delivery-log]"
if (Test-Path $LineDir) {
    $LatestLog = Get-ChildItem -Path $LineDir -Filter "line_delivery_log_*.csv" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime |
        Select-Object -Last 1
    if ($LatestLog) {
        Write-Host $LatestLog.FullName
        Import-Csv -Path $LatestLog.FullName -Encoding UTF8 |
            Select-Object -Last 5 |
            Format-Table -AutoSize
    }
    else {
        Write-Host "missing"
    }
}
else {
    Write-Host "missing"
}

Write-Host ""
Write-Host "[latest-status]"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $ProjectRoot "scripts\show_latest_status.ps1")

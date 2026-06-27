param(
    [switch]$DownloadArtifacts
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [Text.UTF8Encoding]::new()

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$CloudCheck = Join-Path $ProjectRoot "scripts\check_cloud_delivery.ps1"

Write-Host "ETF Rotation Go-Live Cloud Check"
Write-Host ""

Write-Host "1/2 Daily ETF LINE"
$DailyArgs = @("-File", $CloudCheck, "-RequireSuccess")
if ($DownloadArtifacts) {
    $DailyArgs += "-DownloadLatestArtifact"
}
& powershell.exe -NoProfile -ExecutionPolicy Bypass @DailyArgs

Write-Host ""
Write-Host "2/2 Weekly ETF PDCA"
$WeeklyArgs = @("-File", $CloudCheck, "-Weekly", "-RequireSuccess")
if ($DownloadArtifacts) {
    $WeeklyArgs += "-DownloadLatestArtifact"
}
& powershell.exe -NoProfile -ExecutionPolicy Bypass @WeeklyArgs

Write-Host ""
Write-Host "Go-live cloud check completed."

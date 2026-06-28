param(
    [switch]$DownloadArtifacts,
    [switch]$ScheduleOnly
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [Text.UTF8Encoding]::new()

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$CloudCheck = Join-Path $ProjectRoot "scripts\check_cloud_delivery.ps1"

Write-Host "ETF Rotation Go-Live Cloud Check"
Write-Host ""

Write-Host "1/2 Daily ETF LINE"
$DailyArgs = @{
    RequireSuccess = $true
}
if ($ScheduleOnly) {
    $DailyArgs.Event = "schedule"
}
if ($DownloadArtifacts) {
    $DailyArgs.DownloadLatestArtifact = $true
}
& $CloudCheck @DailyArgs

Write-Host ""
Write-Host "2/2 Weekly ETF PDCA"
$WeeklyArgs = @{
    Weekly = $true
    RequireSuccess = $true
}
if ($ScheduleOnly) {
    $WeeklyArgs.Event = "schedule"
}
if ($DownloadArtifacts) {
    $WeeklyArgs.DownloadLatestArtifact = $true
}
& $CloudCheck @WeeklyArgs

Write-Host ""
Write-Host "Go-live cloud check completed."

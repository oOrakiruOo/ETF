param(
    [int]$Limit = 5,
    [switch]$DownloadLatestArtifact
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [Text.UTF8Encoding]::new()

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Gh = "C:\Program Files\GitHub CLI\gh.exe"
$Workflow = "Daily ETF LINE"

if (-not (Test-Path -LiteralPath $Gh)) {
    throw "GitHub CLI not found: $Gh"
}

Write-Host "ETF Rotation Cloud Delivery Check"
Write-Host ""

Write-Host "[runs]"
& $Gh run list --workflow $Workflow --limit $Limit

$LatestJson = & $Gh run list --workflow $Workflow --limit 1 --json databaseId,conclusion,status,event,createdAt,updatedAt,url
$Latest = $LatestJson | ConvertFrom-Json | Select-Object -First 1
if (-not $Latest) {
    Write-Host ""
    Write-Host "[latest] missing"
    exit 0
}

Write-Host ""
Write-Host "[latest]"
$Latest | Format-List

Write-Host ""
Write-Host "[log-summary]"
& $Gh run view $Latest.databaseId --log |
    Select-String -Pattern "日次レポート|LINEへ買い判断|line_delivery|failure alert|Artifact daily-reports|failed" |
    Select-Object -First 40

if ($DownloadLatestArtifact) {
    $OutputDir = Join-Path $ProjectRoot "tmp\actions-daily-reports-$($Latest.databaseId)"
    Write-Host ""
    Write-Host "[download-artifact] $OutputDir"
    if (Test-Path -LiteralPath $OutputDir) {
        $ResolvedOutputDir = (Resolve-Path -LiteralPath $OutputDir).Path
        $AllowedRoot = (Resolve-Path -LiteralPath (Join-Path $ProjectRoot "tmp")).Path
        if (-not $ResolvedOutputDir.StartsWith($AllowedRoot, [StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to remove outside tmp: $ResolvedOutputDir"
        }
        Remove-Item -LiteralPath $OutputDir -Recurse -Force
    }
    & $Gh run download $Latest.databaseId -n daily-reports -D $OutputDir
    Get-ChildItem -Path $OutputDir -Recurse -File | Select-Object -First 30 FullName, Length
}

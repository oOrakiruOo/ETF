param(
    [int]$Limit = 5,
    [switch]$DownloadLatestArtifact,
    [switch]$Weekly,
    [switch]$RequireSuccess,
    [ValidateSet("any", "schedule", "workflow_dispatch")]
    [string]$Event = "any",
    [double]$MaxAgeHours = 0
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [Text.UTF8Encoding]::new()

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Gh = "C:\Program Files\GitHub CLI\gh.exe"
$Workflow = if ($Weekly) { "Weekly ETF PDCA" } else { "Daily ETF LINE" }
$ArtifactName = if ($Weekly) { "weekly-pdca-reports" } else { "daily-reports" }
$ArtifactPrefix = if ($Weekly) { "actions-weekly-pdca" } else { "actions-daily-reports" }
$LogPattern = if ($Weekly) {
    "週次PDCA|軽量履歴再生|週次ヘルス|週次要約|line_delivery|failure alert|Artifact weekly-pdca-reports|failed"
} else {
    "日次レポート|LINEへ買い判断|line_delivery|failure alert|Artifact daily-reports|failed"
}

if (-not (Test-Path -LiteralPath $Gh)) {
    throw "GitHub CLI not found: $Gh"
}

Write-Host "ETF Rotation Cloud Delivery Check"
Write-Host "Workflow: $Workflow"
Write-Host "Event: $Event"
if ($MaxAgeHours -gt 0) {
    Write-Host "MaxAgeHours: $MaxAgeHours"
}
Write-Host ""

Write-Host "[runs]"
& $Gh run list --workflow $Workflow --limit $Limit

$RunListJson = & $Gh run list --workflow $Workflow --limit 20 --json databaseId,conclusion,status,event,createdAt,updatedAt,url
$Runs = @($RunListJson | ConvertFrom-Json)
$Latest = if ($Event -eq "any") {
    $Runs | Select-Object -First 1
} else {
    $Runs | Where-Object { $_.event -eq $Event } | Select-Object -First 1
}
if (-not $Latest) {
    Write-Host ""
    Write-Host "[latest] missing"
    exit 0
}

Write-Host ""
Write-Host "[latest]"
$Latest | Format-List

if ($RequireSuccess -and $Latest.status -ne "completed") {
    throw "$Workflow latest run is not completed: status=$($Latest.status)"
}
if ($RequireSuccess -and $Latest.conclusion -ne "success") {
    throw "$Workflow latest run is not success: conclusion=$($Latest.conclusion)"
}
if ($MaxAgeHours -gt 0) {
    $CreatedAt = [DateTimeOffset]::Parse($Latest.createdAt)
    $AgeHours = ([DateTimeOffset]::UtcNow - $CreatedAt.ToUniversalTime()).TotalHours
    if ($AgeHours -gt $MaxAgeHours) {
        throw "$Workflow latest $Event run is too old: ageHours=$([Math]::Round($AgeHours, 1)) maxAgeHours=$MaxAgeHours"
    }
}

Write-Host ""
Write-Host "[log-summary]"
& $Gh run view $Latest.databaseId --log |
    Select-String -Pattern $LogPattern |
    Select-Object -First 40

if ($DownloadLatestArtifact) {
    $OutputDir = Join-Path $ProjectRoot "tmp\$ArtifactPrefix-$($Latest.databaseId)"
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
    & $Gh run download $Latest.databaseId -n $ArtifactName -D $OutputDir
    Get-ChildItem -Path $OutputDir -Recurse -File | Select-Object -First 30 FullName, Length

    Write-Host ""
    Write-Host "[check-these-first]"
    $Patterns = if ($Weekly) {
        @(
            "reports\weekly\weekly_line_summary_*.txt",
            "reports\weekly\weekly_health_*.md",
            "reports\weekly\weekly_report_*.md",
            "reports\weekly\replay_pdca_report_*.md",
            "data\processed\line\line_delivery_log_*.csv"
        )
    } else {
        @(
            "reports\daily\decision_brief_*.txt",
            "reports\daily\daily_report_*.md",
            "data\processed\line\line_delivery_log_*.csv",
            "data\processed\decisions\manual_decision_sheet_*.csv"
        )
    }
    foreach ($Pattern in $Patterns) {
        $Matched = Get-ChildItem -Path $OutputDir -Recurse -File |
            Where-Object { $_.FullName -like "*$($Pattern.Replace('\', '*'))" } |
            Sort-Object LastWriteTime |
            Select-Object -Last 1
        if ($Matched) {
            Write-Host "- $($Matched.FullName)"
        } else {
            Write-Host "- missing: $Pattern"
        }
    }
}

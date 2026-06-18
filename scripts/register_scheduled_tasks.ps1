param(
    [string]$TaskPrefix = "MASATO ETF Rotation",
    [string]$PortfolioCheckTime = "07:20",
    [string]$DailyOpsTime = "07:25",
    [string]$DailyTime = "07:30",
    [string]$NotificationSummaryTime = "07:35",
    [string]$NotificationPlanTime = "07:37",
    [string]$NotificationPacketsTime = "07:38",
    [string]$LineSummaryTime = "07:55",
    [string]$DailyHealthTime = "07:40",
    [string]$OperationsStatusTime = "07:45",
    [string]$GoLiveCheckTime = "07:50",
    [string]$DecisionSheetTime = "07:39",
    [string]$WeeklyDay = "SAT",
    [string]$WeeklyTime = "08:00",
    [string]$ReplayQuickDay = "SUN",
    [string]$ReplayQuickTime = "08:30",
    [string]$WeeklyHealthDay = "SUN",
    [string]$WeeklyHealthTime = "08:50",
    [bool]$AllowStartOnBattery = $true,
    [switch]$IncludeLineSummary,
    [switch]$Force,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Runner = Join-Path $ProjectRoot "scripts\run_workflow.ps1"

if (-not (Test-Path -LiteralPath $Runner)) {
    throw "Workflow runner not found: $Runner"
}

$Tasks = @(
    @{
        Name = "$TaskPrefix Daily Ops"
        Command = "daily-ops"
        Schedule = "DAILY"
        Time = $DailyOpsTime
        Day = $null
    },
    @{
        Name = "$TaskPrefix Portfolio Check"
        Command = "portfolio-check"
        Schedule = "DAILY"
        Time = $PortfolioCheckTime
        Day = $null
    },
    @{
        Name = "$TaskPrefix Daily"
        Command = "daily"
        Schedule = "DAILY"
        Time = $DailyTime
        Day = $null
    },
    @{
        Name = "$TaskPrefix Notification Summary"
        Command = "notification-summary"
        Schedule = "DAILY"
        Time = $NotificationSummaryTime
        Day = $null
    },
    @{
        Name = "$TaskPrefix Notification Plan"
        Command = "notification-plan"
        Schedule = "DAILY"
        Time = $NotificationPlanTime
        Day = $null
    },
    @{
        Name = "$TaskPrefix Notification Packets"
        Command = "notification-packets"
        Schedule = "DAILY"
        Time = $NotificationPacketsTime
        Day = $null
    },
    @{
        Name = "$TaskPrefix Decision Sheet"
        Command = "decision-sheet"
        Schedule = "DAILY"
        Time = $DecisionSheetTime
        Day = $null
    },
    @{
        Name = "$TaskPrefix Daily Health"
        Command = "daily-health"
        Schedule = "DAILY"
        Time = $DailyHealthTime
        Day = $null
    },
    @{
        Name = "$TaskPrefix Operations Status"
        Command = "operations-status"
        Schedule = "DAILY"
        Time = $OperationsStatusTime
        Day = $null
    },
    @{
        Name = "$TaskPrefix Go Live Check"
        Command = "go-live-check"
        Schedule = "DAILY"
        Time = $GoLiveCheckTime
        Day = $null
    },
    @{
        Name = "$TaskPrefix Weekly"
        Command = "weekly"
        Schedule = "WEEKLY"
        Time = $WeeklyTime
        Day = $WeeklyDay
    },
    @{
        Name = "$TaskPrefix Replay Quick"
        Command = "replay-quick"
        Schedule = "WEEKLY"
        Time = $ReplayQuickTime
        Day = $ReplayQuickDay
    },
    @{
        Name = "$TaskPrefix Weekly Health"
        Command = "weekly-health"
        Schedule = "WEEKLY"
        Time = $WeeklyHealthTime
        Day = $WeeklyHealthDay
    }
)

if ($IncludeLineSummary) {
    $Tasks += @(
        @{
            Name = "$TaskPrefix LINE Summary"
            Command = "line-summary"
            Schedule = "DAILY"
            Time = $LineSummaryTime
            Day = $null
        }
    )
}

foreach ($Task in $Tasks) {
    $TaskRun = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$Runner`" -Command $($Task.Command)"
    $Arguments = @(
        "/Create",
        "/TN", $Task.Name,
        "/TR", $TaskRun,
        "/SC", $Task.Schedule,
        "/ST", $Task.Time
    )

    if ($Task.Day) {
        $Arguments += @("/D", $Task.Day)
    }
    if ($Force) {
        $Arguments += "/F"
    }

    if ($DryRun) {
        $DisplayArguments = $Arguments | ForEach-Object {
            if ($_ -match "\s") {
                "`"$_`""
            }
            else {
                $_
            }
        }
        Write-Host "schtasks.exe $($DisplayArguments -join ' ')"
        continue
    }

    & schtasks.exe @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to register scheduled task: $($Task.Name)"
    }

    if ($AllowStartOnBattery) {
        $RegisteredTask = Get-ScheduledTask -TaskName $Task.Name
        $RegisteredTask.Settings.DisallowStartIfOnBatteries = $false
        $RegisteredTask.Settings.StopIfGoingOnBatteries = $false
        $RegisteredTask.Settings.StartWhenAvailable = $true
        $RegisteredTask.Settings.WakeToRun = $true
        Set-ScheduledTask -InputObject $RegisteredTask | Out-Null
    }
}

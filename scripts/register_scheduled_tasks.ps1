param(
    [string]$TaskPrefix = "MASATO ETF Rotation",
    [string]$DailyTime = "07:30",
    [string]$WeeklyDay = "SAT",
    [string]$WeeklyTime = "08:00",
    [string]$ReplayQuickDay = "SUN",
    [string]$ReplayQuickTime = "08:30",
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
        Name = "$TaskPrefix Daily"
        Command = "daily"
        Schedule = "DAILY"
        Time = $DailyTime
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
    }
)

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
}

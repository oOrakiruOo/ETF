param(
    [switch]$OpenChatGpt,
    [switch]$PasteToChatGpt,
    [switch]$Submit,
    [int]$WaitSeconds = 8
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [Text.UTF8Encoding]::new()

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$PromptPath = Join-Path $ProjectRoot "docs\chatgpt_handoff_prompt.md"

if (-not (Test-Path -LiteralPath $PromptPath)) {
    throw "Prompt file not found: $PromptPath"
}

$Text = Get-Content -Path $PromptPath -Raw -Encoding UTF8
$Matches = [regex]::Matches($Text, '```text\r?\n(?<prompt>[\s\S]*?)\r?\n```')
if ($Matches.Count -eq 0) {
    throw "No text prompt block found in: $PromptPath"
}

$Prompt = $Matches[0].Groups["prompt"].Value.Trim()
Set-Clipboard -Value $Prompt

Write-Host "ChatGPT handoff prompt copied to clipboard."
Write-Host "Source: $PromptPath"
Write-Host "Characters: $($Prompt.Length)"

$ShouldOpen = $OpenChatGpt -or $PasteToChatGpt -or $Submit
if ($ShouldOpen) {
    Start-Process "https://chatgpt.com/"
}

if ($PasteToChatGpt -or $Submit) {
    Start-Sleep -Seconds $WaitSeconds

    Add-Type -AssemblyName System.Windows.Forms
    $Shell = New-Object -ComObject WScript.Shell
    $Activated = $false
    foreach ($Title in @("ChatGPT", "OpenAI", "Google Chrome", "Microsoft Edge", "Firefox", "Brave")) {
        if ($Shell.AppActivate($Title)) {
            $Activated = $true
            break
        }
    }

    if (-not $Activated) {
        throw "Could not activate the ChatGPT browser window. Open ChatGPT, click the input box, then run again."
    }

    [System.Windows.Forms.SendKeys]::SendWait("^v")
    Write-Host "Prompt pasted into the active ChatGPT window."

    if ($Submit) {
        Start-Sleep -Milliseconds 500
        [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
        Write-Host "Prompt submitted to ChatGPT."
    }
}

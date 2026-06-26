param(
    [switch]$OpenChatGpt
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

if ($OpenChatGpt) {
    Start-Process "https://chatgpt.com/"
}

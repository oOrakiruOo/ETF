param(
    [string]$ToUserId
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [Text.UTF8Encoding]::new()

if (-not $ToUserId) {
    $ToUserId = Read-Host "LINE_TO_USER_ID"
}

$SecureToken = Read-Host "LINE_CHANNEL_ACCESS_TOKEN" -AsSecureString
$TokenPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureToken)
try {
    $Token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($TokenPointer)
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($TokenPointer)
}

if (-not $Token) {
    throw "LINE_CHANNEL_ACCESS_TOKEN is empty."
}
if (-not $ToUserId) {
    throw "LINE_TO_USER_ID is empty."
}

[Environment]::SetEnvironmentVariable("LINE_CHANNEL_ACCESS_TOKEN", $Token, "User")
[Environment]::SetEnvironmentVariable("LINE_TO_USER_ID", $ToUserId, "User")

$env:LINE_CHANNEL_ACCESS_TOKEN = $Token
$env:LINE_TO_USER_ID = $ToUserId

Write-Host "LINE environment variables saved to Windows user environment."
Write-Host "Open a new PowerShell and run: .\scripts\run_workflow.ps1 -Command line-check"

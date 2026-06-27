param(
    [string]$ProjectPath = "D:\Codex\ai-content-factory",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [Text.UTF8Encoding]::new()

$Target = [System.IO.Path]::GetFullPath($ProjectPath)

if ((Test-Path -LiteralPath $Target) -and -not $Force) {
    throw "Target already exists: $Target. Use -Force only when you intentionally want to add missing scaffold files."
}

New-Item -ItemType Directory -Force -Path $Target | Out-Null
foreach ($Name in @("inputs", "prompts", "outputs", "scripts", "config")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $Target $Name) | Out-Null
}

$Files = @{
    "AGENTS.md" = @"
# AGENTS.md

## Project

Small Python CLI tool for generating draft content.

## Rules

- Keep changes minimal.
- Mock first.
- Do not add external integrations unless asked.
- Do not read unrelated folders.
- Output Markdown files under `outputs/`.
- Do not store secrets in the repo.
"@
    "README.md" = @"
# ai-content-factory

Lightweight side-project repository for content draft generation.

## Goal

Start small. Use `--mock` first, then add real API integration later.

## Folders

- `inputs/`: source topics or notes
- `prompts/`: prompt templates
- `outputs/`: generated Markdown
- `scripts/`: CLI scripts
- `config/`: local settings

## First Codex Task

Use the template from the ETF repository:

```text
New small repository.
Do not use ETF context.
Build a mock-first Python CLI v0.1.
```
"@
    "requirements.txt" = @"
"@
    ".env.example" = @"
# Add API keys later.
# OPENAI_API_KEY=
"@
    ".gitignore" = @"
__pycache__/
*.py[cod]
.venv/
.env
outputs/
tmp/
"@
    "inputs/themes.md" = @"
# Themes

- sample-theme
"@
}

foreach ($RelativePath in $Files.Keys) {
    $Path = Join-Path $Target $RelativePath
    if ((Test-Path -LiteralPath $Path) -and -not $Force) {
        continue
    }
    $Parent = Split-Path -Parent $Path
    New-Item -ItemType Directory -Force -Path $Parent | Out-Null
    Set-Content -Path $Path -Value $Files[$RelativePath] -Encoding UTF8
}

$Git = "C:\Program Files\Git\cmd\git.exe"
if ((Test-Path -LiteralPath $Git) -and -not (Test-Path -LiteralPath (Join-Path $Target ".git"))) {
    & $Git -C $Target init | Out-Null
}

Write-Host "Side project scaffold ready:"
Write-Host $Target

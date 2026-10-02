$ErrorActionPreference = 'Stop'
$userData = Join-Path $env:LOCALAPPDATA 'SmolVLA-VSCode'
$settingsDirectory = Join-Path $userData 'User'
New-Item -ItemType Directory -Force $settingsDirectory | Out-Null
$settingsFile = Join-Path $settingsDirectory 'settings.json'
if (-not (Test-Path -LiteralPath $settingsFile)) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'vscode-user-settings.json') -Destination $settingsFile
}
& code --user-data-dir $userData --new-window --remote ssh-remote+nlp-pc-2026 /home/alexander/projects/smolvla-sim
if ($LASTEXITCODE -ne 0) { throw 'VS Code could not open PC1' }

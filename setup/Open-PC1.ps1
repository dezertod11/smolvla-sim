param([switch]$Container, [switch]$PrepareOnly)
$ErrorActionPreference = 'Stop'
$userData = Join-Path $env:LOCALAPPDATA 'SmolVLA-VSCode'
$settingsDirectory = Join-Path $userData 'User'
New-Item -ItemType Directory -Force $settingsDirectory | Out-Null
$settingsFile = Join-Path $settingsDirectory 'settings.json'
if (-not (Test-Path -LiteralPath $settingsFile)) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'vscode-user-settings.json') -Destination $settingsFile
}
# Repair only project-critical settings; preserve the user's other preferences.
# Fail without overwriting if the existing file cannot be parsed.
$settings = Get-Content -Raw -LiteralPath $settingsFile | ConvertFrom-Json
$dockerPath = '/home/alexander/projects/smolvla-sim/scripts/docker.sh'
$ignored = @($settings.'settingsSync.ignoredSettings' | Where-Object { $_ })
$changed = $settings.'dev.containers.dockerPath' -ne $dockerPath -or
    $ignored -notcontains 'dev.containers.dockerPath' -or
    $ignored -contains '-dev.containers.dockerPath'
if ($changed) {
    $backupDirectory = Join-Path $userData 'settings-backups'
    New-Item -ItemType Directory -Force $backupDirectory | Out-Null
    $backupName = 'settings-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '.json'
    Copy-Item -LiteralPath $settingsFile -Destination (Join-Path $backupDirectory $backupName)
    $settings | Add-Member -Force NoteProperty 'dev.containers.dockerPath' $dockerPath
    $ignored = @($ignored | Where-Object { $_ -ne '-dev.containers.dockerPath' })
    $ignored = @(@($ignored) + @('dev.containers.dockerPath') | Select-Object -Unique)
    $settings | Add-Member -Force NoteProperty 'settingsSync.ignoredSettings' $ignored
    $json = $settings | ConvertTo-Json -Depth 100
    [IO.File]::WriteAllText($settingsFile, $json + [Environment]::NewLine, [Text.UTF8Encoding]::new($false))
}
if ($PrepareOnly) { return }
if ($Container) {
    try { & (Join-Path $PSScriptRoot 'Start-PC1Proxy.ps1') }
    catch { Write-Warning ("Codex network: " + $_.Exception.Message) }
    & ssh -T -o BatchMode=yes -o ConnectTimeout=15 nlp-pc-2026 `
        'cd /home/alexander/projects/smolvla-sim && bash scripts/start_control.sh'
    if ($LASTEXITCODE -ne 0) { Write-Warning 'Experiment control worker could not start.' }
    $metadata = '{"hostPath":"/home/alexander/projects/smolvla-sim","localDocker":false,"configFile":{"$mid":1,"path":"/home/alexander/projects/smolvla-sim/.devcontainer/devcontainer.json","scheme":"vscode-fileHost"}}'
    $hex = ([BitConverter]::ToString([Text.Encoding]::UTF8.GetBytes($metadata))).Replace('-', '').ToLowerInvariant()
    $uri = 'vscode-remote://dev-container+' + $hex + '@ssh-remote+nlp-pc-2026/workspace'
    & code --user-data-dir $userData --new-window --folder-uri $uri
} else {
    & code --user-data-dir $userData --new-window --remote ssh-remote+nlp-pc-2026 /home/alexander/projects/smolvla-sim
}
if ($LASTEXITCODE -ne 0) { throw 'VS Code could not open PC1' }

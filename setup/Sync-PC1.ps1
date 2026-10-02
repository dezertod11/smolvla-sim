param([switch]$Pull)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$remoteRoot = '/home/alexander/projects/smolvla-sim'
if (& git -C $root status --porcelain) { throw 'Commit or preserve laptop changes before syncing.' }
if ($Pull) {
    & ssh nlp-pc-2026 "git -C $remoteRoot push origin main"
    if ($LASTEXITCODE -ne 0) { throw 'PC1 push failed' }
    & git -C $root pull --ff-only
} else {
    & git -C $root push origin main
    if ($LASTEXITCODE -ne 0) { throw 'Laptop push failed' }
    & ssh nlp-pc-2026 "git -C $remoteRoot pull --ff-only"
}
if ($LASTEXITCODE -ne 0) { throw 'Sync stopped; inspect local changes or divergent commits.' }

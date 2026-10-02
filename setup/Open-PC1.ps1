$ErrorActionPreference = 'Stop'
& code --new-window --remote ssh-remote+nlp-pc-2026 /home/alexander/projects/smolvla-sim
if ($LASTEXITCODE -ne 0) { throw 'VS Code could not open PC1' }

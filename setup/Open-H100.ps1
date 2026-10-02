$ErrorActionPreference = 'Stop'
& ssh -t nlp-pc-2026 'bash /home/alexander/projects/smolvla-sim/scripts/h100_ssh.sh --interactive'
if ($LASTEXITCODE -ne 0) { throw 'H100 connection failed' }

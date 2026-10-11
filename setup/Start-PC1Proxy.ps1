param([switch]$Worker, [switch]$Stop)
$ErrorActionPreference = 'Stop'
$runtime = Join-Path $PSScriptRoot '..\.runtime\codex-network'
New-Item -ItemType Directory -Force -Path $runtime | Out-Null
$runtime = (Resolve-Path -LiteralPath $runtime).Path
$stopFile = Join-Path $runtime 'stop'
$pidFile = Join-Path $runtime 'worker.pid'
$sshExe = Join-Path $env:WINDIR 'System32\OpenSSH\ssh.exe'
$scriptFile = $PSCommandPath

function Get-ProxyWorker {
    if (Test-Path -LiteralPath $pidFile) {
        $workerId = Get-Content -LiteralPath $pidFile -Raw
        if ($workerId.Trim() -match '^\d+$') {
            $p = Get-CimInstance Win32_Process -Filter "ProcessId = $($workerId.Trim())"
            if ($p -and $p.Name -eq 'powershell.exe' -and
                $p.CommandLine.Contains($scriptFile) -and $p.CommandLine.Contains('-Worker')) {
                return $p
            }
        }
    }
}

if ($Stop) {
    [IO.File]::WriteAllText($stopFile, 'stop')
    for ($i = 0; $i -lt 15 -and (Get-ProxyWorker); $i++) { Start-Sleep -Seconds 1 }
    if (Get-ProxyWorker) { throw 'Proxy worker has not stopped; inspect .runtime/codex-network.' }
    Write-Host 'Project proxy tunnel stopped.'
    return
}

if (-not $Worker) {
    $tcp = [Net.Sockets.TcpClient]::new()
    try {
        $pending = $tcp.BeginConnect('127.0.0.1', 10809, $null, $null)
        if (-not $pending.AsyncWaitHandle.WaitOne(2000)) { throw 'Happ proxy timed out.' }
        $tcp.EndConnect($pending)
    } catch {
        throw 'Connect Happ on this laptop first (HTTP proxy 127.0.0.1:10809).'
    } finally { $tcp.Dispose() }
    if (Get-ProxyWorker) { return }
    if (Test-Path -LiteralPath $stopFile) { Remove-Item -LiteralPath $stopFile }
    $p = Start-Process -FilePath 'powershell.exe' -ArgumentList @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"' + $scriptFile + '"'), '-Worker'
    ) -WindowStyle Hidden -PassThru
    for ($i = 0; $i -lt 10; $i++) {
        Start-Sleep -Milliseconds 500
        if (Get-ProxyWorker) { return }
        if ($p.HasExited) { throw 'Project proxy worker exited before startup.' }
    }
    throw 'Project proxy worker did not start. Inspect .runtime/codex-network.'
}

# A session-local mutex prevents duplicate workers from simultaneous launches.
$mutex = [Threading.Mutex]::new($false, 'Local\SmolVLA-PC1-Happ-Proxy')
$locked = $false
$child = $null
try {
    try { $locked = $mutex.WaitOne(0) } catch [Threading.AbandonedMutexException] { $locked = $true }
    if (-not $locked) { return }
    [IO.File]::WriteAllText($pidFile, [string]$PID)
    while (-not (Test-Path -LiteralPath $stopFile)) {
        # Remote listener is Windows loopback only, never LAN/0.0.0.0.
        # Docker Desktop reaches it through host.docker.internal.
        $arguments = @('-NT', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15',
            '-o', 'ExitOnForwardFailure=yes', '-o', 'ServerAliveInterval=15',
            '-o', 'ServerAliveCountMax=3', '-o', 'StrictHostKeyChecking=yes',
            '-o', 'HostKeyAlias=10.8.1.2', '-i', ($env:USERPROFILE + '/.ssh/id_remote_pc'),
            '-R', '127.0.0.1:18089:127.0.0.1:10809', 'Alexander@100.90.225.13')
        $child = Start-Process -FilePath $sshExe -ArgumentList $arguments -WindowStyle Hidden -PassThru `
            -RedirectStandardError (Join-Path $runtime 'ssh.stderr.log') `
            -RedirectStandardOutput (Join-Path $runtime 'ssh.stdout.log')
        while (-not $child.HasExited -and -not (Test-Path -LiteralPath $stopFile)) {
            Start-Sleep -Seconds 2
        }
        if (-not $child.HasExited) { $child.Kill(); $child.WaitForExit() }
        $child.Dispose()
        $child = $null
        # Back off and reconnect after a network change or laptop wake-up.
        for ($i = 0; $i -lt 5 -and -not (Test-Path -LiteralPath $stopFile); $i++) {
            Start-Sleep -Seconds 2
        }
    }
} finally {
    if ($child) {
        if (-not $child.HasExited) { $child.Kill(); $child.WaitForExit() }
        $child.Dispose()
    }
    if ($locked) {
        if (Test-Path -LiteralPath $pidFile) { Remove-Item -LiteralPath $pidFile }
        $mutex.ReleaseMutex()
    }
    $mutex.Dispose()
}

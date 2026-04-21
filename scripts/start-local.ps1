Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$rootDir = Split-Path -Parent $PSScriptRoot
$runDir = Join-Path $rootDir ".run"
$backendPidFile = Join-Path $runDir "backend.pid"
$frontendPidFile = Join-Path $runDir "frontend.pid"
$backendLog = Join-Path $runDir "backend.log"
$backendErrLog = Join-Path $runDir "backend.err.log"
$frontendLog = Join-Path $runDir "frontend.log"
$frontendErrLog = Join-Path $runDir "frontend.err.log"
$frontendDir = Join-Path $rootDir "frontend\web"

if (-not (Test-Path $runDir)) {
    New-Item -ItemType Directory -Path $runDir | Out-Null
}

function Import-DotEnv {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        return
    }

    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            return
        }

        $parts = $line -split "=", 2
        if ($parts.Count -ne 2) {
            return
        }

        [Environment]::SetEnvironmentVariable($parts[0], $parts[1], "Process")
    }
}

function Get-ProcessFromPidFile {
    param([string]$PidFile)

    if (-not (Test-Path $PidFile)) {
        return $null
    }

    $pidValue = (Get-Content $PidFile -Raw).Trim()
    if (-not $pidValue) {
        return $null
    }

    try {
        return Get-Process -Id ([int]$pidValue) -ErrorAction Stop
    } catch {
        Remove-Item $PidFile -ErrorAction SilentlyContinue
        return $null
    }
}

function Get-RepoFrontendProcess {
    $normalizedFrontendDir = $frontendDir.Replace("\", "\\")
    $process = Get-CimInstance Win32_Process | Where-Object {
        $_.Name -eq "node.exe" -and
        $_.CommandLine -like "*$normalizedFrontendDir*" -and
        $_.CommandLine -like "*next*dev*"
    } | Select-Object -First 1

    if (-not $process) {
        return $null
    }

    try {
        return Get-Process -Id $process.ProcessId -ErrorAction Stop
    } catch {
        return $null
    }
}

Import-DotEnv (Join-Path $rootDir ".env")

$databaseUrl = if ($env:DATABASE_URL) { $env:DATABASE_URL } else { "sqlite:///./meddiag.local.db" }

$pythonExe = if (Test-Path (Join-Path $rootDir ".venv\Scripts\python.exe")) {
    Join-Path $rootDir ".venv\Scripts\python.exe"
} else {
    "python"
}

if ($databaseUrl.StartsWith("postgresql")) {
    Write-Host "Starting PostgreSQL container..."
    docker compose up -d db | Out-Null

    Write-Host "Waiting for PostgreSQL on 127.0.0.1:5432..."
    $deadline = (Get-Date).AddSeconds(60)
    $ready = $false
    while ((Get-Date) -lt $deadline) {
        try {
            $client = New-Object System.Net.Sockets.TcpClient
            $async = $client.BeginConnect("127.0.0.1", 5432, $null, $null)
            $connected = $async.AsyncWaitHandle.WaitOne(1000)
            if ($connected -and $client.Connected) {
                $client.EndConnect($async)
                $client.Close()
                $ready = $true
                break
            }
            $client.Close()
        } catch {
        }
        Start-Sleep -Seconds 1
    }

    if (-not $ready) {
        throw "PostgreSQL did not become reachable on 127.0.0.1:5432."
    }
} else {
    Write-Host "Using SQLite local database: $databaseUrl"
}

Write-Host "Checking database connectivity..."
& $pythonExe (Join-Path $rootDir "scripts\check-local-db.py")

$backendProcess = Get-ProcessFromPidFile $backendPidFile
if ($backendProcess) {
    Write-Host "Backend already running with PID $($backendProcess.Id)."
} else {
    Write-Host "Starting backend on http://127.0.0.1:8000 ..."
    $backend = Start-Process -FilePath $pythonExe `
        -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000") `
        -WorkingDirectory $rootDir `
        -RedirectStandardOutput $backendLog `
        -RedirectStandardError $backendErrLog `
        -PassThru
    Set-Content -Path $backendPidFile -Value $backend.Id
}

$frontendProcess = Get-ProcessFromPidFile $frontendPidFile
if (-not $frontendProcess) {
    $frontendProcess = Get-RepoFrontendProcess
    if ($frontendProcess) {
        Set-Content -Path $frontendPidFile -Value $frontendProcess.Id
    }
}
if ($frontendProcess) {
    Write-Host "Frontend already running with PID $($frontendProcess.Id)."
} else {
    Write-Host "Starting frontend on http://127.0.0.1:3000 ..."
    $nextCli = Join-Path $frontendDir "node_modules\next\dist\bin\next"
    if (-not (Test-Path $nextCli)) {
        throw "Next.js dependencies are not installed in frontend\web. Run npm install first."
    }

    $nodeExe = "node"
    $frontendArgs = "`"$nextCli`" dev --hostname 127.0.0.1 --port 3000"
    $frontend = Start-Process -FilePath $nodeExe `
        -ArgumentList $frontendArgs `
        -WorkingDirectory $frontendDir `
        -RedirectStandardOutput $frontendLog `
        -RedirectStandardError $frontendErrLog `
        -PassThru
    Set-Content -Path $frontendPidFile -Value $frontend.Id
}

Write-Host ""
Write-Host "Local services started:"
Write-Host "  Backend:  http://127.0.0.1:8000"
Write-Host "  Frontend: http://127.0.0.1:3000"
Write-Host ""
Write-Host "Logs:"
Write-Host "  Backend:  $backendLog"
Write-Host "  Backend stderr: $backendErrLog"
Write-Host "  Frontend: $frontendLog"
Write-Host "  Frontend stderr: $frontendErrLog"

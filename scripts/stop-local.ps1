Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$rootDir = Split-Path -Parent $PSScriptRoot
$runDir = Join-Path $rootDir ".run"
$backendPidFile = Join-Path $runDir "backend.pid"
$frontendPidFile = Join-Path $runDir "frontend.pid"
$frontendDir = Join-Path $rootDir "frontend\web"

function Stop-TrackedProcess {
    param(
        [string]$Label,
        [string]$PidFile
    )

    if (-not (Test-Path $PidFile)) {
        Write-Host "$Label is not tracked as running."
        return
    }

    $pidValue = (Get-Content $PidFile -Raw).Trim()
    if ($pidValue) {
        try {
            $process = Get-Process -Id ([int]$pidValue) -ErrorAction Stop
            Write-Host "Stopping $Label (PID $($process.Id))..."
            Stop-Process -Id $process.Id -Force
        } catch {
            Write-Host "$Label PID file exists but process is not running."
        }
    }

    Remove-Item $PidFile -ErrorAction SilentlyContinue
}

function Stop-RepoFrontendProcesses {
    $normalizedFrontendDir = $frontendDir.Replace("\", "\\")
    $processes = Get-CimInstance Win32_Process | Where-Object {
        $_.Name -eq "node.exe" -and
        $_.CommandLine -like "*$normalizedFrontendDir*" -and
        $_.CommandLine -like "*next*dev*"
    }

    foreach ($process in $processes) {
        try {
            Write-Host "Stopping frontend node process (PID $($process.ProcessId))..."
            Stop-Process -Id $process.ProcessId -Force
        } catch {
        }
    }
}

Stop-TrackedProcess -Label "backend" -PidFile $backendPidFile
Stop-TrackedProcess -Label "frontend" -PidFile $frontendPidFile
Stop-RepoFrontendProcesses

try {
    docker compose stop db | Out-Null
    Write-Host "Stopped PostgreSQL container (if it was running)."
} catch {
}

Write-Host "Done."

$ErrorActionPreference = 'Stop'
$pnsiRoot = $PSScriptRoot
$pnsiPython = Join-Path $pnsiRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pnsiPython)) { throw 'Install the dependencies using README.md first.' }
foreach ($pnsiPort in @(3001,8001)) {
    $pnsiSocket = [Net.Sockets.TcpClient]::new()
    $pnsiOccupied = $false
    try { $pnsiSocket.Connect('127.0.0.1',$pnsiPort); $pnsiOccupied = $true }
    catch { $pnsiOccupied = $false }
    finally { $pnsiSocket.Dispose() }
    if ($pnsiOccupied) { throw "Port $pnsiPort is in use. Open http://127.0.0.1:3001 or close the existing local PNSI session first." }
}
$pnsiData = Join-Path $pnsiRoot 'data'
New-Item -ItemType Directory -Path $pnsiData -Force | Out-Null
$pnsiCodeFile = Join-Path $pnsiData 'local-setup-code.txt'
if (-not (Test-Path -LiteralPath $pnsiCodeFile)) {
    $pnsiRandom = New-Object byte[] 32
    [Security.Cryptography.RandomNumberGenerator]::Fill($pnsiRandom)
    [Convert]::ToHexString($pnsiRandom) | Set-Content -LiteralPath $pnsiCodeFile
}
$env:APP_ENV = 'local'
$env:LOCAL_SETUP_CODE = (Get-Content -LiteralPath $pnsiCodeFile -Raw).Trim()
$env:DATABASE_URL = 'sqlite:///' + (Join-Path $pnsiData 'pnsi-local.db').Replace('\','/')
$env:API_INTERNAL_URL = 'http://127.0.0.1:8001'
$env:NEXT_TELEMETRY_DISABLED = '1'
if (Test-Path -LiteralPath (Join-Path $pnsiData 'pnsi-local.db')) {
    & $pnsiPython (Join-Path $pnsiRoot 'scripts\backup-local.py')
    if ($LASTEXITCODE -ne 0) { throw 'Backup failed; inspect the database before starting.' }
}
$pnsiApi = $null
$pnsiWorker = $null
try {
    $pnsiApi = Start-Process -FilePath $pnsiPython -ArgumentList @('-m','uvicorn','apps.api.main:app','--host','127.0.0.1','--port','8001') -WorkingDirectory $pnsiRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $pnsiData 'api.log') -RedirectStandardError (Join-Path $pnsiData 'api-error.log')
    $pnsiReady = $false
    for ($pnsiAttempt = 0; $pnsiAttempt -lt 20; $pnsiAttempt++) {
        if ($pnsiApi.HasExited) { throw 'API startup failed. See data/api-error.log.' }
        try { $pnsiHealth = Invoke-RestMethod 'http://127.0.0.1:8001/health/ready' -TimeoutSec 1; $pnsiReady = $pnsiHealth.status -eq 'ready' }
        catch { $pnsiReady = $false }
        if ($pnsiReady) { break }
        Start-Sleep -Milliseconds 250
    }
    if (-not $pnsiReady) { throw 'API readiness check failed. See data/api-error.log.' }
    $pnsiWorker = Start-Process -FilePath $pnsiPython -ArgumentList @('workers/run.py') -WorkingDirectory $pnsiRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $pnsiData 'worker.log') -RedirectStandardError (Join-Path $pnsiData 'worker-error.log')
    Write-Host 'PNSI local: http://127.0.0.1:3001'
    $pnsiAuthConfig = Invoke-RestMethod 'http://127.0.0.1:8001/api/v1/auth/config'
    if (-not $pnsiAuthConfig.configured) {
        Write-Host 'First setup code (only needed before the first account is created):'
        Write-Host $env:LOCAL_SETUP_CODE
    }
    Set-Location (Join-Path $pnsiRoot 'apps\web')
    npm run build
    if ($LASTEXITCODE -ne 0) { throw 'Web build failed.' }
    npm run start -- --port 3001
}
finally {
    foreach ($pnsiProcess in @($pnsiApi,$pnsiWorker)) { if ($pnsiProcess) { Stop-Process -Id $pnsiProcess.Id -ErrorAction SilentlyContinue } }
    Set-Location $pnsiRoot
}

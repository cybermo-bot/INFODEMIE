$ErrorActionPreference = 'Stop'
$pnsiRoot = $PSScriptRoot
$pnsiPython = Join-Path $pnsiRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pnsiPython)) { throw 'Run the setup instructions in README.md first.' }
$pnsiLog = Join-Path $pnsiRoot 'artifacts'
New-Item -ItemType Directory -Path $pnsiLog -Force | Out-Null
$pnsiApi = Start-Process -FilePath $pnsiPython -ArgumentList @('-m','uvicorn','apps.api.main:app','--host','127.0.0.1','--port','8000') -WorkingDirectory $pnsiRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $pnsiLog 'api.log') -RedirectStandardError (Join-Path $pnsiLog 'api-error.log')
$pnsiWorker = Start-Process -FilePath $pnsiPython -ArgumentList @('workers/run.py') -WorkingDirectory $pnsiRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $pnsiLog 'worker.log') -RedirectStandardError (Join-Path $pnsiLog 'worker-error.log')
Write-Host 'API: http://127.0.0.1:8000/docs | Web: http://127.0.0.1:3000'
Write-Host "API process: $($pnsiApi.Id); worker: $($pnsiWorker.Id)"
try { Set-Location (Join-Path $pnsiRoot 'apps\web'); npm run dev }
finally { Stop-Process -Id $pnsiApi.Id,$pnsiWorker.Id -ErrorAction SilentlyContinue }

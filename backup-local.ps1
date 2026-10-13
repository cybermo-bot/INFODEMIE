$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot '.venv\Scripts\python.exe') (Join-Path $PSScriptRoot 'scripts\backup-local.py')
if ($LASTEXITCODE -ne 0) { throw 'Local backup failed.' }

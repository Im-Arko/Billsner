$ErrorActionPreference = 'Stop'
Push-Location (Join-Path $PSScriptRoot 'frontend')
try {
    if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
        throw 'Install Node.js, reopen PowerShell, and run this script again.'
    }
    if (-not (Test-Path -LiteralPath 'node_modules')) {
        & npm.cmd ci
        if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
    }
    & npm.cmd run dev -- --host 127.0.0.1
    if ($LASTEXITCODE -ne 0) { throw 'The frontend stopped with an error.' }
}
finally { Pop-Location }

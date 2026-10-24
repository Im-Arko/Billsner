param([switch]$InstallDependencies, [int]$Port = 8000)
$ErrorActionPreference = 'Stop'
Push-Location (Join-Path $PSScriptRoot 'backend')
try {
    $pythonExe = Join-Path (Get-Location) '.venv\Scripts\python.exe'
    $newEnvironment = -not (Test-Path -LiteralPath $pythonExe)
    if ($newEnvironment) {
        if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 -m venv .venv }
        else { & python -m venv .venv }
        if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment. Install Python 3.12 or 3.13.' }
    }
    & $pythonExe -c "import importlib.util, sys; sys.exit(not all(importlib.util.find_spec(m) is not None for m in ('fastapi', 'sqlalchemy', 'aiosqlite', 'httpx', 'cv2', 'pytesseract', 'pandas', 'openpyxl', 'reportlab', 'jose', 'bcrypt', 'slowapi', 'email_validator', 'multipart', 'pdf2image', 'uvicorn', 'pydantic_settings')))"
    $dependenciesMissing = $LASTEXITCODE -ne 0
    if ($newEnvironment -or $InstallDependencies -or $dependenciesMissing) {
        & $pythonExe -m pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Check the error above.' }
    }
    if (-not (Test-Path -LiteralPath '.env')) {
        $appSecret = & $pythonExe -c "import secrets; print(secrets.token_hex(32))"
        (Get-Content -LiteralPath '.env.example' -Raw).Replace('generate-a-random-secret', $appSecret) |
            Set-Content -LiteralPath '.env' -Encoding utf8
        Write-Host 'Created backend/.env. Add GROQ_API_KEY there and restart this script.'
    }
    Write-Host "Starting API and built-in bill worker at http://localhost:$Port"
    & $pythonExe -m uvicorn app.main:app --host 127.0.0.1 --port $Port --workers 1
    if ($LASTEXITCODE -ne 0) { throw 'The backend stopped with an error. Check the output above.' }
}
finally { Pop-Location }

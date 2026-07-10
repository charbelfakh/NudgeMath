# Starts NudgeMath: GraphQL backend + Vite frontend, each in its own window.
# Usage:  .\start.ps1
# Stop:   close the two spawned windows (or Ctrl+C in each).

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

# --- sanity checks -----------------------------------------------------------
$venvActivate = Join-Path $root ".venv\Scripts\Activate.ps1"
if (-not (Test-Path $venvActivate)) {
    Write-Error "No virtualenv found at .venv - create it first: python -m venv .venv ; pip install -r requirements.txt"
}
if (-not (Test-Path (Join-Path $root "frontend\node_modules"))) {
    Write-Warning "frontend\node_modules missing - running 'npm install' first."
    Push-Location (Join-Path $root "frontend")
    npm install
    Pop-Location
}

# --- vision model for the photo -> hint feature ------------------------------
# The project default (llama3.2-vision) may not be pulled. Fall back to a
# locally available vision model so image transcription works out of the box.
# Override by setting LLM_VISION_MODEL yourself before running this script.
# Child processes started below inherit this environment variable.
if (-not $env:LLM_VISION_MODEL) {
    $env:LLM_VISION_MODEL = "qwen3.5:9b"
}
Write-Host "Vision model      -> $env:LLM_VISION_MODEL (photo -> hint)" -ForegroundColor Cyan

# --- admin session secret ----------------------------------------------------
# Signs admin login tokens so sessions survive backend restarts. Persisted in
# the gitignored .nudgemath/ dir (never committed); auto-generated once if absent.
# Override by setting NUDGEMATH_AUTH_SECRET yourself before running this script.
# Child processes started below inherit this environment variable.
if (-not $env:NUDGEMATH_AUTH_SECRET) {
    $secretFile = Join-Path $root ".nudgemath\auth_secret"
    if (-not (Test-Path $secretFile)) {
        New-Item -ItemType Directory -Force -Path (Split-Path $secretFile) | Out-Null
        $rngBytes = New-Object 'System.Byte[]' 32
        [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($rngBytes)
        (-join ($rngBytes | ForEach-Object { $_.ToString('x2') })) |
            Set-Content -NoNewline -Encoding ascii $secretFile
    }
    $env:NUDGEMATH_AUTH_SECRET = (Get-Content -Raw $secretFile).Trim()
}
Write-Host "Auth secret       -> loaded (admin sessions persist across restarts)" -ForegroundColor Cyan

# --- backend: GraphQL API on http://127.0.0.1:8000/graphql -------------------
Write-Host "Starting backend  -> http://127.0.0.1:8000/graphql" -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "& '$venvActivate'; Set-Location '$root'; uvicorn hint_engine.api.app:app --reload"
)

# --- frontend: Vite dev server on http://localhost:5173 ----------------------
Write-Host "Starting frontend -> http://localhost:5173" -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location '$root\frontend'; npm run dev"
)

Write-Host ""
Write-Host "Both servers launching in separate windows." -ForegroundColor Green
Write-Host "  Backend : http://127.0.0.1:8000/graphql"
Write-Host "  Frontend: http://localhost:5173"
Write-Host "Close those windows (or Ctrl+C in each) to stop."

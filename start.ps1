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

# Starts the DCF dashboard: FastAPI backend (8000) + Vite frontend (5173).
# Usage: .\run.ps1   then open http://localhost:5173

$root = $PSScriptRoot

if (-not (Test-Path "$root\backend\.venv")) {
    Write-Host "Creating Python venv and installing backend dependencies..."
    python -m venv "$root\backend\.venv"
    & "$root\backend\.venv\Scripts\python.exe" -m pip install -r "$root\backend\requirements.txt"
}

if (-not (Test-Path "$root\frontend\node_modules")) {
    Write-Host "Installing frontend dependencies..."
    npm --prefix "$root\frontend" install
}

Write-Host "Starting backend on http://localhost:8000 ..."
$backend = Start-Process -FilePath "$root\backend\.venv\Scripts\python.exe" `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--port", "8000" `
    -WorkingDirectory "$root\backend" -PassThru -WindowStyle Hidden

try {
    Write-Host "Starting frontend on http://localhost:5173 ... (Ctrl+C stops both)"
    npm --prefix "$root\frontend" run dev
} finally {
    if ($backend -and -not $backend.HasExited) {
        Stop-Process -Id $backend.Id -Force
        Write-Host "Backend stopped."
    }
}

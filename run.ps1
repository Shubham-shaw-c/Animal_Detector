Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "        ANIMAL AI - DETECTION & CHATBOT DASHBOARD" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Starting application server..." -ForegroundColor Green
Write-Host ""

if (Test-Path ".\venv\Scripts\python.exe") {
    Write-Host "[*] Using project virtual environment (venv)..." -ForegroundColor Yellow
    & ".\venv\Scripts\python.exe" "app.py"
} else {
    Write-Host "[*] Using system python..." -ForegroundColor Yellow
    python app.py
}


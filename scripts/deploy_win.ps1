# scripts/deploy_win.ps1
# Environment: Windows (PowerShell)
# Purpose: Automate Docker deployment for Frank Gemini on Windows Server

# Error handling
$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "[INFO] Starting Frank Gemini Windows Auto-Deployment (v1.1.1)" -ForegroundColor Cyan
Write-Host "=========================================================="

# 1. Check Docker status
try {
    docker version > $null
} catch {
    Write-Host "[ERROR] Cannot connect to Docker. Please ensure Docker Desktop is running." -ForegroundColor Red
    exit
}

# 2. Build Base Image
Write-Host ""
Write-Host "[STEP 1] Building/Verifying base environment image (dream-base)..." -ForegroundColor Yellow
docker build -t dream-base:latest -f Dockerfile.base .

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Base image build failed. Check network connection." -ForegroundColor Red
    exit
}

# 3. Start Application
Write-Host ""
Write-Host "[STEP 2] Starting business containers (dream-frank)..." -ForegroundColor Yellow
docker compose up -d --build

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Business container failed to start." -ForegroundColor Red
    exit
}

# 4. Status Check
Write-Host ""
Write-Host "[SUCCESS] Deployment complete! Syncing container status..." -ForegroundColor Green
Start-Sleep -Seconds 2
docker ps --filter "name=dream_frank_gemini"

Write-Host ""
Write-Host "[MONITOR] Real-time logs (Press Ctrl+C to exit log view, container will keep running):" -ForegroundColor Gray
Write-Host "----------------------------------------------------------"
docker compose logs -f --tail 30

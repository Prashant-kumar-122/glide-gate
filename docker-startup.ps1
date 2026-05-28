# GlideGate Docker Startup Script for Windows PowerShell
# Run with: .\docker-startup.ps1

Write-Host "==========================================" -ForegroundColor Green
Write-Host "GlideGate Local Development Setup" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green

Write-Host "`nPrerequisites Check:" -ForegroundColor Blue
Write-Host "Docker Desktop installed and running"
Write-Host "Ports available: 5432, 8000, 5173"

Write-Host "`nBuilding & Starting Services:" -ForegroundColor Blue

if (-not (Test-Path ".env.docker")) {
    Write-Host "WARNING: .env.docker not found!" -ForegroundColor Red
    Write-Host "Creating .env.docker with defaults..."
}

Write-Host "Starting Docker containers..." -ForegroundColor Yellow
docker-compose --env-file .env.docker up -d

Write-Host "`nWaiting for PostgreSQL to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host "`nChecking PostgreSQL Health:" -ForegroundColor Blue
$pgHealthy = docker-compose exec -T postgres pg_isready -U postgres -d glide_gate
if ($LASTEXITCODE -eq 0) {
    Write-Host "PostgreSQL is ready" -ForegroundColor Green
} else {
    Write-Host "PostgreSQL is not ready" -ForegroundColor Red
    exit 1
}

Write-Host "`nWaiting for backend migrations to complete..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

Write-Host "`nChecking Backend Health:" -ForegroundColor Blue
$maxAttempts = 30
$attempt = 0
while ($attempt -lt $maxAttempts) {
    try {
        $response = docker-compose exec -T backend curl -s http://localhost:8000/api/health
        if ($response) {
            Write-Host "Backend API is healthy" -ForegroundColor Green
            break
        }
    } catch {
        $attempt++
        Write-Host "Attempt $attempt/$maxAttempts : Waiting for backend..."
        Start-Sleep -Seconds 2
    }
}

Write-Host "`nChecking Frontend:" -ForegroundColor Blue
$frontendRunning = docker ps | Select-String "glide_gate_frontend"
if ($frontendRunning) {
    Write-Host "Frontend is running" -ForegroundColor Green
} else {
    Write-Host "Frontend is not running" -ForegroundColor Yellow
}

Write-Host "`n==========================================" -ForegroundColor Green
Write-Host "All Services Started Successfully!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green

Write-Host "`nService URLs:" -ForegroundColor Blue
Write-Host "  Frontend:  http://localhost:5173" -ForegroundColor Green
Write-Host "  Backend:   http://localhost:8000" -ForegroundColor Green
Write-Host "  API Docs:  http://localhost:8000/api/docs" -ForegroundColor Green
Write-Host "  PostgreSQL: localhost:5432" -ForegroundColor Green

Write-Host "`nContainer Status:" -ForegroundColor Blue
docker-compose ps

Write-Host "`nUseful Commands:" -ForegroundColor Yellow
Write-Host "  View logs:           docker-compose logs -f"
Write-Host "  View backend logs:   docker-compose logs -f backend"
Write-Host "  View frontend logs:  docker-compose logs -f frontend"
Write-Host "  Stop services:       docker-compose down"
Write-Host "  Stop and remove:     docker-compose down -v"
Write-Host "  Restart services:    docker-compose restart"
Write-Host "`n"

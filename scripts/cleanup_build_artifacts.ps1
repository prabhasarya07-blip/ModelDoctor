$ErrorActionPreference = "Stop"

Write-Host "Cleaning build/cache artifacts..." -ForegroundColor Cyan

$paths = @(
  "modeldoctor-frontend/.next",
  "modeldoctor-frontend/node_modules",
  "modeldoctor-backend/__pycache__",
  "modeldoctor-backend/models/__pycache__",
  "modeldoctor-backend/routers/__pycache__",
  "modeldoctor-backend/services/__pycache__",
  "modeldoctor-backend/utils/__pycache__"
)

foreach ($p in $paths) {
  if (Test-Path $p) {
    Write-Host "Removing $p"
    Remove-Item -Recurse -Force $p
  }
}

# Remove compiled Python artifacts
Get-ChildItem -Recurse -Force -File modeldoctor-backend -Filter *.pyc -ErrorAction SilentlyContinue | Remove-Item -Force

Write-Host "Done." -ForegroundColor Green


<#
PowerShell helper: create a short-path virtual environment and install deps.

Usage (PowerShell):
  Open PowerShell (not as Admin), then run:
    .\scripts\setup_short_venv.ps1

What it does:
  - creates venv at C:\venv\yieldsense
  - activates it for the script session
  - upgrades pip
  - installs requirements from repo but skips 'torch' to avoid long-path extraction issues
  - provides an optional command to install PyTorch separately

Note: Adjust PYTORCH_INSTALL_CMD if you need a specific CUDA wheel.
#>

$venvPath = "C:\venv\yieldsense"
$requirements = "requirements.txt"

Write-Host "Creating virtual environment at $venvPath ..."
if (-Not (Test-Path $venvPath)) {
    python -m venv $venvPath
} else {
    Write-Host "Venv already exists at $venvPath"
}

$activate = Join-Path $venvPath "Scripts\Activate.ps1"
Write-Host "Activating venv..."
. $activate

Write-Host "Upgrading pip..."
python -m pip install --upgrade pip

Write-Host "Installing requirements (excluding torch)..."
$tmpReq = "$env:TEMP\requirements_no_torch.txt"
Get-Content $requirements | Where-Object { $_ -notmatch '^\s*torch' } | Set-Content $tmpReq
python -m pip install -r $tmpReq

Write-Host "Finished installing non-torch requirements."

Write-Host "To install PyTorch (CPU wheel), run:" -ForegroundColor Yellow
Write-Host "pip install --index-url https://download.pytorch.org/whl/cpu torch" -ForegroundColor Cyan

Write-Host "Or visit https://pytorch.org/get-started/locally/ for platform-specific wheel commands." -ForegroundColor Cyan

Write-Host "Done. To activate venv in a new shell run:`"`n$activate`"`n" -ForegroundColor Green

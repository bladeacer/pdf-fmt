<#
.SYNOPSIS
Installs dependencies for the pdf-fmt project.

.DESCRIPTION
Clones the repository, creates a Python virtual environment,
installs 'uv', and installs project dependencies from requirements.txt.
Exits immediately on any command failure.
#>

# PowerShell equivalent of 'set -e': ensures script exits on non-terminating errors.
$ErrorActionPreference = "Stop"

$RepoUrl = "https://github.com/bladeacer/pdf-fmt"
$VenvPath = ".\.venv"
$ActivationScript = "$VenvPath\Scripts\Activate.ps1"

# -------------------- 1. Clone the repository --------------------
Write-Host "Cloning repository..."
git clone --depth 1 $RepoUrl

# -------------------- 2. Create the virtual environment --------------------
Write-Host "Creating virtual environment..."
python -m venv $VenvPath

# -------------------- 3. Install 'uv' into the environment --------------------
# Note: For PowerShell, we execute the 'activate' script directly in the current session
# to make 'uv' available later. This uses the dot-sourcing operator (.).
Write-Host "Activating environment and installing uv..."
. $ActivationScript
python -m pip install uv

# -------------------- 4. Install dependencies using uv --------------------
# uv is now available in the activated shell session
Write-Host "Installing dependencies from requirements.txt..."
uv pip install -r requirements.txt

# -------------------- Final Confirmation --------------------
Write-Host ""
Write-Host "Setup complete! The environment is currently active." -ForegroundColor Green
Write-Host "To re-activate it later, run: . $ActivationScript"

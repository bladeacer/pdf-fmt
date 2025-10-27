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
$RepoName = "pdf-fmt"
$VenvPath = ".\.venv"
$ActivationScript = "$VenvPath\Scripts\Activate.ps1"

# --- Confirmation Block ---
Write-Host "
This script will install the 'pdf-fmt' command-line tool.

It will perform the following actions in the current location:
1. Clone the '$RepoName' repository from GitHub.
2. Change into the new 'pdf-fmt' directory.
3. Create a Python virtual environment named '.venv'.
4. Install the 'uv' package manager and all required Python dependencies (like PyMuPDF).

Do you want to proceed with the installation? (y/N): "
$Confirmation = Read-Host

if ($Confirmation -ne "y" -and $Confirmation -ne "Y") {
    Write-Host "Installation cancelled by the user."
    exit 0
}
# --------------------------

Write-Host "Starting installation..."

# 1. Clone the repository
Write-Host "Cloning repository..."
git clone --depth 1 $RepoUrl

# Change into the cloned directory for subsequent commands
Set-Location $RepoName

# 2. Create the virtual environment
Write-Host "Creating virtual environment..."
python -m venv $VenvPath

# 3. Install 'uv' into the environment
Write-Host "Activating environment and installing uv..."
. $ActivationScript
python -m pip install uv

# 4. Install dependencies using uv
Write-Host "Installing dependencies from requirements-ci.txt..."
uv pip install -r requirements-ci.txt

# -------------------- Final Confirmation --------------------
Write-Host ""
Write-Host "Setup complete! The environment is currently active." -ForegroundColor Green
Write-Host "To re-activate it later, run: ." $ActivationScript "from within the $RepoName directory."
Write-Host "Then execute: pdf-fmt <file.pdf>"

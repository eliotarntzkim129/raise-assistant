$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = $null
foreach ($candidate in @("py -3.13", "py -3.12", "py -3.11", "py -3.10", "python")) {
  try {
    $parts = $candidate.Split(" ")
    $arguments = @()
    if ($parts.Length -gt 1) { $arguments = $parts[1..($parts.Length - 1)] }
    & $parts[0] @arguments -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" 2>$null
    if ($LASTEXITCODE -eq 0) { $python = $candidate; break }
  } catch {}
}
if (-not $python) { throw "Python 3.10 or newer is required. Install Python 3.11 and try again." }

$p = $python.Split(" ")
$arguments = @()
if ($p.Length -gt 1) { $arguments = $p[1..($p.Length - 1)] }
if (-not (Test-Path ".venv")) { & $p[0] @arguments -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install -e .
if ($LASTEXITCODE -ne 0) { throw "Package installation failed. Ask IT for access to an approved Python package index (PIP_INDEX_URL), then rerun setup.ps1." }
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }
& .\.venv\Scripts\python.exe scripts\configure.py
New-Item -ItemType Directory -Force data\uploads, exports, knowledge\private | Out-Null
Write-Host "Setup complete. Start the app with .\run.ps1"


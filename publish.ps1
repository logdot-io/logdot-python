[CmdletBinding()]
param(
    [switch]$Bump
)

$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot

try {
    # Read current version from pyproject.toml
    $pyproject = Get-Content "pyproject.toml" -Raw
    if ($pyproject -match 'version\s*=\s*"([^"]+)"') {
        $currentVersion = $Matches[1]
    } else {
        throw "Could not parse version from pyproject.toml"
    }

    if ($Bump) {
        $parts = $currentVersion.Split('.')
        $newPatch = [int]$parts[2] + 1
        $newVersion = "$($parts[0]).$($parts[1]).$newPatch"

        Write-Host "Bumping version: ${currentVersion} -> ${newVersion}"

        # Update pyproject.toml
        (Get-Content "pyproject.toml") -replace "version = `"${currentVersion}`"", "version = `"${newVersion}`"" |
            Set-Content "pyproject.toml"

        # Update logdot/__init__.py
        (Get-Content "logdot/__init__.py") -replace "__version__ = `"${currentVersion}`"", "__version__ = `"${newVersion}`"" |
            Set-Content "logdot/__init__.py"

        $currentVersion = $newVersion
    }

    Write-Host "Publishing logdot-io-sdk v${currentVersion}..."

    Write-Host "Cleaning dist/..."
    if (Test-Path "dist") { Remove-Item "dist" -Recurse -Force }

    Write-Host "Building..."
    python -m build
    if ($LASTEXITCODE -ne 0) { throw "Build failed" }

    Write-Host "Publishing to PyPI..."
    twine upload dist/*
    if ($LASTEXITCODE -ne 0) { throw "Publish failed" }

    Write-Host "Successfully published logdot-io-sdk v${currentVersion}"
}
finally {
    Pop-Location
}

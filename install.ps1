$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot

if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv tool install --editable $ScriptDir --force
} elseif (Get-Command pipx -ErrorAction SilentlyContinue) {
    pipx install --editable $ScriptDir --force
} else {
    Write-Error "neither 'uv' nor 'pipx' found on PATH"
    exit 1
}

Write-Host "apmw installed — run 'apmw --help' to verify."

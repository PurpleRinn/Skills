[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$Destination,
    [switch]$Replace
)

$ErrorActionPreference = "Stop"
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$source = Join-Path $repositoryRoot "genie"

if (-not (Test-Path -LiteralPath (Join-Path $source "SKILL.md"))) {
    throw "Genie source was not found: $source"
}

if (-not $Destination) {
    $codexRoot = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
    $Destination = Join-Path (Join-Path $codexRoot "skills") "genie"
}

$destinationParent = Split-Path -Parent $Destination
New-Item -ItemType Directory -Force -Path $destinationParent | Out-Null

if (Test-Path -LiteralPath $Destination) {
    if (-not $Replace) {
        throw "Genie is already installed at $Destination. Re-run with -Replace to update it."
    }

    $skillFile = Join-Path $Destination "SKILL.md"
    if (-not (Test-Path -LiteralPath $skillFile) -or -not (Select-String -LiteralPath $skillFile -Pattern '^name:\s*genie\s*$' -Quiet)) {
        throw "The existing destination is not a Genie installation: $Destination"
    }

    if ($PSCmdlet.ShouldProcess($Destination, "Replace the existing Genie installation")) {
        Remove-Item -LiteralPath $Destination -Recurse -Force
    } else {
        return
    }
}

if ($PSCmdlet.ShouldProcess($Destination, "Install Genie")) {
    Copy-Item -LiteralPath $source -Destination $Destination -Recurse
    Write-Output "Genie installed: $Destination"
    Write-Output "It will be available in the next Codex conversation."
}

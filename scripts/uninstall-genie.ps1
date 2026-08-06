[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = "High")]
param(
    [string]$Destination
)

$ErrorActionPreference = "Stop"

if (-not $Destination) {
    $codexRoot = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
    $Destination = Join-Path (Join-Path $codexRoot "skills") "genie"
}

if (-not (Test-Path -LiteralPath $Destination)) {
    Write-Output "Genie is not installed: $Destination"
    return
}

$resolvedDestination = (Resolve-Path -LiteralPath $Destination).Path
$resolvedParent = (Resolve-Path -LiteralPath (Split-Path -Parent $Destination)).Path
$expected = Join-Path $resolvedParent "genie"
$skillFile = Join-Path $resolvedDestination "SKILL.md"

if ($resolvedDestination -ne $expected) {
    throw "Refusing to remove an unexpected path: $resolvedDestination"
}

if (-not (Test-Path -LiteralPath $skillFile) -or -not (Select-String -LiteralPath $skillFile -Pattern '^name:\s*genie\s*$' -Quiet)) {
    throw "The target is not a Genie installation: $resolvedDestination"
}

if ($PSCmdlet.ShouldProcess($resolvedDestination, "Uninstall the complete Genie skill pack")) {
    Remove-Item -LiteralPath $resolvedDestination -Recurse -Force
    Write-Output "Genie uninstalled. Project history under docs/genie was preserved."
}

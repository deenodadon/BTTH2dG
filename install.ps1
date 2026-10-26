# Downloads the Ikemen GO engine (free, open-source MUGEN-compatible) and installs
# the Battle Through the Heavens 2.5D characters and stages into it.
# usage (PowerShell):  .\install.ps1 [-Dest C:\Games\BTTH]
param([string]$Dest = "$PSScriptRoot\ikemen")
$ErrorActionPreference = "Stop"
if (-not (Test-Path "$Dest\data")) {
    Write-Host "Looking up the latest Ikemen GO release..."
    $rel = Invoke-RestMethod "https://api.github.com/repos/ikemen-engine/Ikemen-GO/releases/latest"
    $asset = $rel.assets | Where-Object { $_.name -match "win" -and $_.name -match "\.zip$" -and $_.name -notmatch "x86|32" } | Select-Object -First 1
    if (-not $asset) { throw "No Windows zip found. Download Ikemen GO manually from https://github.com/ikemen-engine/Ikemen-GO/releases, unzip it to $Dest and re-run." }
    $tmp = Join-Path $env:TEMP ("ikemen_" + [guid]::NewGuid())
    New-Item -ItemType Directory $tmp | Out-Null
    Write-Host "Downloading $($asset.browser_download_url)"
    Invoke-WebRequest $asset.browser_download_url -OutFile "$tmp\ikemen.zip"
    Expand-Archive "$tmp\ikemen.zip" "$tmp\x"
    $data = Get-ChildItem "$tmp\x" -Recurse -Directory -Filter data | Select-Object -First 1
    New-Item -ItemType Directory -Force $Dest | Out-Null
    Copy-Item "$($data.Parent.FullName)\*" $Dest -Recurse -Force
    Remove-Item $tmp -Recurse -Force
}
Write-Host "Installing characters and stages into $Dest"
New-Item -ItemType Directory -Force "$Dest\chars", "$Dest\stages" | Out-Null
Copy-Item "$PSScriptRoot\game\chars\*" "$Dest\chars" -Recurse -Force
Copy-Item "$PSScriptRoot\game\stages\*" "$Dest\stages" -Recurse -Force
if ((Test-Path "$Dest\data\select.def") -and -not (Test-Path "$Dest\data\select.def.orig")) {
    Copy-Item "$Dest\data\select.def" "$Dest\data\select.def.orig"
}
Copy-Item "$PSScriptRoot\game\data\select.def" "$Dest\data\select.def" -Force
Write-Host "Done. Run $Dest\Ikemen_GO.exe"

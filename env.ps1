$RUN_DIR = (Get-Location).Path
Write-Host $RUN_DIR

$thisFilePath = $MyInvocation.MyCommand.Path
$SCRIPT_DIR = Split-Path -Path $thisFilePath -Parent
Write-Host $SCRIPT_DIR

Set-Location $SCRIPT_DIR

uv venv --python  ">=3.10,<=3.12"
.venv\Scripts\activate
uv sync

$env:Path += ";$SCRIPT_DIR\pycmds"

Set-Location $RUN_DIR

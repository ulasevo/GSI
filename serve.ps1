# Start the local GSI authoring server for desktop and phone
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ($scriptDir) {
    Set-Location $scriptDir
    $env:PYTHONPATH = "$scriptDir;$env:PYTHONPATH"
}
python tools/serve.py @args

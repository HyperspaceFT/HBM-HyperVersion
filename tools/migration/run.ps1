[CmdletBinding(PositionalBinding = $false)]
param(
    [string]$Python = '',
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$ToolArguments
)

$ErrorActionPreference = 'Stop'
if (-not $Python) {
    foreach ($candidate in @('python', 'python3')) {
        $pythonCommand = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($pythonCommand -and $pythonCommand.Source -notlike '*WindowsApps*') {
            $Python = $pythonCommand.Source
            break
        }
    }
}
if (-not $Python) {
    $bundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    if (Test-Path -LiteralPath $bundledPython -PathType Leaf) { $Python = $bundledPython }
}
if (-not $Python) {
    throw 'Python 3.11+ was not found. Supply -Python with an existing Python executable. Nothing was installed.'
}

& $Python -B -X utf8 (Join-Path $PSScriptRoot 'migration.py') @ToolArguments
exit $LASTEXITCODE

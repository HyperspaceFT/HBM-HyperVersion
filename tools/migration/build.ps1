[CmdletBinding(PositionalBinding = $false)]
param(
    [string]$JavaHome = '',
    [string]$GradleUserHome = '',
    [switch]$Offline,
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$GradleArguments
)

$ErrorActionPreference = 'Stop'
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))

function Test-Java21([string]$Candidate) {
    if (-not $Candidate) { return $false }
    $releaseFile = Join-Path $Candidate 'release'
    $javaFile = Join-Path $Candidate 'bin/java.exe'
    return (Test-Path -LiteralPath $javaFile -PathType Leaf) -and
        (Test-Path -LiteralPath $releaseFile -PathType Leaf) -and
        [bool](Select-String -LiteralPath $releaseFile -Pattern '^JAVA_VERSION="21(?:\.|"|-)')
}

if ($JavaHome -and -not (Test-Java21 $JavaHome)) {
    throw "The selected Java home is not an existing Java 21 installation: $JavaHome"
}
if (-not $JavaHome) {
    $candidates = @($env:JAVA_HOME)
    if ($env:ProgramFiles) { $candidates += Join-Path $env:ProgramFiles 'Java/jdk-21' }
    $javaCommand = Get-Command java -ErrorAction SilentlyContinue
    if ($javaCommand) { $candidates += Split-Path (Split-Path $javaCommand.Source -Parent) -Parent }
    $JavaHome = $candidates | Where-Object { Test-Java21 $_ } | Select-Object -First 1
}
if (-not $JavaHome) {
    throw 'Java 21 was not found. Supply -JavaHome with an existing JDK 21 directory. No JDK is downloaded.'
}
if (-not $GradleUserHome) { $GradleUserHome = Join-Path $repoRoot '.gradle/user-home' }
$GradleUserHome = [System.IO.Path]::GetFullPath($GradleUserHome)

if ($Offline) {
    # Gradle's --offline flag does not cover the wrapper distribution download.
    $wrapperProperties = Join-Path $repoRoot 'gradle/wrapper/gradle-wrapper.properties'
    $distributionLine = (Select-String -LiteralPath $wrapperProperties -Pattern '^distributionUrl=').Line
    if (-not $distributionLine) { throw 'Wrapper distributionUrl is missing.' }
    $distributionUrl = $distributionLine.Substring('distributionUrl='.Length).Replace('\:', ':')
    $distributionName = [System.IO.Path]::GetFileName(([Uri]$distributionUrl).AbsolutePath)
    $md5 = [System.Security.Cryptography.MD5]::Create()
    try { $digest = $md5.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($distributionUrl)) }
    finally { $md5.Dispose() }
    [Array]::Reverse($digest)
    $positiveBytes = [byte[]]($digest + [byte]0)
    $number = [System.Numerics.BigInteger]::new($positiveBytes)
    $alphabet = '0123456789abcdefghijklmnopqrstuvwxyz'
    $distributionKey = ''
    while ($number -gt 0) {
        $remainder = [System.Numerics.BigInteger]::Zero
        $number = [System.Numerics.BigInteger]::DivRem($number, 36, [ref]$remainder)
        $distributionKey = $alphabet[[int]$remainder] + $distributionKey
    }
    $distributionRoot = Join-Path $GradleUserHome ('wrapper/dists/' + $distributionName.Replace('.zip', '') + '/' + $distributionKey)
    $installedMarker = Join-Path $distributionRoot ($distributionName + '.ok')
    if (-not (Test-Path -LiteralPath $installedMarker -PathType Leaf)) {
        throw "Offline wrapper distribution is not installed at $distributionRoot. Run once without -Offline only when downloads are authorized."
    }
}

$temporaryDirectory = Join-Path $repoRoot '.gradle/tmp'
New-Item -ItemType Directory -Force -Path $temporaryDirectory | Out-Null
$savedJavaHome = $env:JAVA_HOME
$savedGradleHome = $env:GRADLE_USER_HOME
$savedJavaOptions = $env:JAVA_TOOL_OPTIONS
$exitCode = 1
Push-Location -LiteralPath $repoRoot
try {
    $env:JAVA_HOME = $JavaHome
    $env:GRADLE_USER_HOME = $GradleUserHome
    # This machine's default temp path fails Java's Unix-domain loopback connector.
    # Keep the workaround process-local and inherited by Gradle's child JVMs.
    $env:JAVA_TOOL_OPTIONS = ($savedJavaOptions + ' -Djdk.net.unixdomain.tmpdir="' + $temporaryDirectory + '" -Djava.io.tmpdir="' + $temporaryDirectory + '"').Trim()
    $wrapperArguments = @('-Porg.gradle.java.installations.auto-download=false', '--console=plain')
    if ($Offline) { $wrapperArguments += '--offline' }
    if ($GradleArguments) { $wrapperArguments += $GradleArguments } else { $wrapperArguments += 'build' }
    & (Join-Path $repoRoot 'gradlew.bat') @wrapperArguments
    $exitCode = $LASTEXITCODE
} finally {
    $env:JAVA_HOME = $savedJavaHome
    $env:GRADLE_USER_HOME = $savedGradleHome
    $env:JAVA_TOOL_OPTIONS = $savedJavaOptions
    Pop-Location
}
exit $exitCode

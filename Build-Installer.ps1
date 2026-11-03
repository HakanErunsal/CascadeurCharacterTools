$ErrorActionPreference = 'Stop'

$compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (-not (Test-Path -LiteralPath $compiler)) {
    $compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework\v4.0.30319\csc.exe'
}
if (-not (Test-Path -LiteralPath $compiler)) {
    throw 'The .NET Framework C# compiler was not found.'
}

& $compiler /nologo /target:winexe /optimize+ `
    "/out:$PSScriptRoot\Install.exe" `
    "/win32icon:$PSScriptRoot\assets\manny-tools.ico" `
    /reference:System.Windows.Forms.dll `
    "$PSScriptRoot\Installer.cs"
if ($LASTEXITCODE -ne 0) {
    throw "Installer build failed with exit code $LASTEXITCODE."
}
Write-Host 'Built Install.exe with the Manny Tools icon.'

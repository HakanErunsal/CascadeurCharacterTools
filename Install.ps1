param([string]$CascadeurPath = 'D:\GameDevelopmentTools\Cascadeur')
$ErrorActionPreference = 'Stop'
$packageRoot = $PSScriptRoot
$scriptsRoot = Join-Path $CascadeurPath 'resources\scripts'
if (-not (Test-Path -LiteralPath (Join-Path $CascadeurPath 'cascadeur.exe'))) { throw 'Choose the folder containing cascadeur.exe with -CascadeurPath.' }
$partsFolder = Join-Path $scriptsRoot 'parts\upc_character_tools'
$commandsFolder = Join-Path $scriptsRoot 'python\scripts\upc_character_tools_menu'
New-Item -ItemType Directory -Path $partsFolder,$commandsFolder -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $packageRoot 'assets\manny.partscasc') -Destination (Join-Path $partsFolder 'manny.partscasc') -Force
Set-Content -LiteralPath (Join-Path $commandsFolder '__init__.py') -Value '' -Encoding utf8
$pythonPathLiteral = ($packageRoot.Replace('\','/').Replace("'","\'"))
$loader = @"
import sys
def name():
    return 'Manny Tools.Character Panel'
def description():
    return 'Add named Manny characters and export normalized root-motion animations.'
def run(scene):
    folder = '$pythonPathLiteral'
    if folder not in sys.path:
        sys.path.insert(0, folder)
    import upc_character_tools
    upc_character_tools.show()
"@
Set-Content -LiteralPath (Join-Path $commandsFolder 'character_panel.py') -Value $loader -Encoding utf8
Write-Host 'Installed. In Cascadeur, reload scripts or restart, then open Scripts > Manny Tools > Character Panel.'

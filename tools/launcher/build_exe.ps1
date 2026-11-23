<#
    Сборка нативного запускателя Kuji.exe.

    Что происходит:
      1. берётся системный компилятор C# (csc.exe из .NET Framework — есть в
         каждой Windows 10/11, Visual Studio не нужна);
      2. компилируется tools\launcher\KujiLauncher.cs в /target:winexe (без
         окна консоли);
      3. иконка assets\icon.ico вшивается в exe ключом /win32icon, поэтому
         Kuji.exe красиво выглядит в проводнике и на панели задач;
      4. (по желанию) создаётся ярлык с этой же иконкой.

    Запуск:  powershell -ExecutionPolicy Bypass -File tools\launcher\build_exe.ps1
    Ключ -Shortcut — дополнительно положить ярлык на Рабочий стол и в корень
    проекта. Kuji.exe — артефакт сборки, в репозиторий не входит (см.
    .gitignore); в git остаётся run_app.cmd.
#>

[CmdletBinding()]
param(
    # Положить ярлык «Kuji.lnk» на Рабочий стол и рядом с Kuji.exe.
    [switch]$Shortcut,

    # Каталог проекта (по умолчанию — два уровня вверх от этого скрипта).
    [string]$Root = ''
)

$ErrorActionPreference = 'Stop'

if (-not $Root) {
    $Root = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
}

$exePath = Join-Path $Root 'Kuji.exe'
$srcPath = Join-Path $Root 'tools\launcher\KujiLauncher.cs'
$iconPath = Join-Path $Root 'assets\icon.ico'

Write-Host 'Kuji: сборка запускателя' -ForegroundColor Cyan

# --------------------------------------------------------------- компилятор
$csc = Get-ChildItem "$env:WINDIR\Microsoft.NET\Framework64\*\csc.exe" -ErrorAction SilentlyContinue |
    Sort-Object FullName -Descending | Select-Object -First 1
if (-not $csc) {
    $csc = Get-ChildItem "$env:WINDIR\Microsoft.NET\*\*\csc.exe" -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending | Select-Object -First 1
}
if (-not $csc) {
    throw 'Не найден csc.exe (.NET Framework). Установите компонент «.NET Framework 4.8».'
}
Write-Host ("  компилятор: {0}" -f $csc.FullName) -ForegroundColor DarkGray

foreach ($p in @($srcPath, $iconPath, (Join-Path $Root 'main.py'))) {
    if (-not (Test-Path $p)) { throw "Нет необходимого файла: $p" }
}

# ------------------------------------------------------------------ сборка
$cscArgs = @(
    '/nologo',
    '/target:winexe',
    '/optimize+',
    "/win32icon:$iconPath",
    '/reference:System.Windows.Forms.dll',
    '/reference:System.Drawing.dll',
    "/out:$exePath",
    $srcPath
)
& $csc.FullName @cscArgs
if ($LASTEXITCODE -ne 0) { throw "csc.exe завершился с кодом $LASTEXITCODE" }

$size = (Get-Item $exePath).Length
Write-Host ("  готово: {0} ({1:N0} байт)" -f $exePath, $size) -ForegroundColor Green

# ------------------------------------------------------------------ ярлык
function New-KujiShortcut([string]$LnkPath) {
    $shell = New-Object -ComObject WScript.Shell
    $lnk = $shell.CreateShortcut($LnkPath)
    $lnk.TargetPath = $exePath
    $lnk.WorkingDirectory = $Root
    $lnk.IconLocation = "$exePath,0"
    $lnk.Description = 'Kuji (Куджи) — конструктор логических деревьев событий'
    $lnk.Save()
    Write-Host ("  ярлык: {0}" -f $LnkPath) -ForegroundColor Green
}

if ($Shortcut) {
    $desktop = [Environment]::GetFolderPath('Desktop')
    New-KujiShortcut (Join-Path $desktop 'Kuji.lnk')
    New-KujiShortcut (Join-Path $Root 'Kuji.lnk')
}

Write-Host 'Дальше: двойной клик по Kuji.exe (или запуск run_app.cmd как раньше).' -ForegroundColor Cyan

<#
    Сборка поставки Kuji (вопрос заказчика про 7z-архив).

    Логика одна и та же для обоих профилей: берется рабочее дерево проекта,
    из него выкладывается чистая папка dist\Kuji (код + встроенная среда +
    Kuji.exe + ярлык-установщик), она ПРОВЕРЯЕТСЯ запуском, и только потом
    пакуется в 7z. Архив из непроверенной папки не выпускается.

    Профили:
      full  — среда как есть (надежный эталон, ~900 МБ на диске).
      thin  — вырезается то, что приложение не импортирует: WebEngine,
              QML/Quick, Designer, PDF, мультимедиа, *.pyi, metatypes,
              неиспользуемые плагины Qt, переводы кроме ru/en. Приложению
              нужны только QtCore / QtGui / QtWidgets / QtSvg (проверено по
              всем import'ам eta\) и pandoc для экспорта в DOCX.

    Запуск:
      powershell -NoProfile -ExecutionPolicy Bypass -File tools\dist\make_dist.ps1
      ... -Profile full        # без урезания среды
      ... -Sfx                 # дополнительно self-extracting exe
      ... -SkipVerify          # не запускать собранную папку (только для отладки)
      ... -Keep                # не удалять dist\Kuji после упаковки

    Ярлык в архиве не хранится как .lnk: .lnk помнит абсолютный путь, и после
    распаковки на другой машине он указывал бы в никуда. Вместо этого кладём
    «Установить ярлык.cmd» — он создаёт Kuji.lnk на Рабочем столе, беря путь
    от своего местоположения.
#>

[CmdletBinding()]
param(
    [ValidateSet('thin', 'full')]
    [string]$Profile = 'thin',

    [string]$Root = '',
    [string]$Out = '',

    # Дополнительно собрать self-extracting exe (распаковка одним двойным
    # кликом; иконка у такого exe остаётся системной 7-Zip).
    [switch]$Sfx,

    [switch]$SkipVerify,
    [switch]$Keep
)

$ErrorActionPreference = 'Stop'

if (-not $Root) {
    $Root = (Get-Item $PSScriptRoot).Parent.Parent.FullName
}
if (-not $Out) { $Out = Join-Path $Root 'dist' }

$stage = Join-Path $Out 'Kuji'

# ---------------------------------------------------------------- версия
$verLine = Select-String -Path (Join-Path $Root 'eta\__init__.py') -Pattern '__version__\s*=\s*"([^"]+)"' |
    Select-Object -First 1
if (-not $verLine) { throw 'Не найдена версия в eta\__init__.py' }
$version = $verLine.Matches[0].Groups[1].Value
$baseName = "Kuji-$version-win64"

Write-Host "Kuji $version | профиль: $Profile" -ForegroundColor Cyan
Write-Host "  корень: $Root" -ForegroundColor DarkGray
Write-Host "  сборка: $stage" -ForegroundColor DarkGray

# ------------------------------------------------------- 1. чистая сцена
if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
New-Item -ItemType Directory -Path $stage -Force | Out-Null

function Copy-Tree([string]$Src, [string]$Dst, [string[]]$ExtraExcludeDirs = @()) {
    if (-not (Test-Path $Src)) { throw "Нет исходника: $Src" }
    $xd = @('__pycache__', '.git', 'dist') + $ExtraExcludeDirs
    # $args — автоматическая переменная PowerShell, её нельзя перезаписывать.
    $robArgs = @($Src, $Dst, '/E', '/NFL', '/NDL', '/NJH', '/NJS', '/NP', '/R:1', '/W:1', '/MT:16',
                 '/XF', '*.pyc', '*.pyo', '*.log')
    foreach ($d in $xd) { $robArgs += '/XD'; $robArgs += (Join-Path $Src $d); $robArgs += $d }
    & robocopy.exe @robArgs | Out-Null
    if ($LASTEXITCODE -gt 7) { throw "robocopy завершился с кодом $LASTEXITCODE ($Src)" }
}

# --------------------------------------------------- 2. код и ресурсы
Write-Host '[1/6] код, ресурсы, запускатель' -ForegroundColor Cyan
foreach ($item in @('main.py', 'eta', 'assets', 'README.md', 'LICENSE', 'run_app.cmd', 'run_app_debug.cmd')) {
    $srcItem = Join-Path $Root $item
    if (-not (Test-Path $srcItem)) { continue }
    if ((Get-Item $srcItem).PSIsContainer) {
        Copy-Tree $srcItem (Join-Path $stage $item)
    } else {
        Copy-Item $srcItem -Destination $stage
    }
}

# Kuji.exe: берём готовый, иначе собираем на месте.
$kujiExe = Join-Path $Root 'Kuji.exe'
if (-not (Test-Path $kujiExe)) {
    & (Join-Path $Root 'tools\launcher\build_exe.ps1')
    $kujiExe = Join-Path $Root 'Kuji.exe'
}
Copy-Item $kujiExe -Destination $stage

# В поставку не входят тесты, отчёты сессий, черновики и служебное.
foreach ($junk in @('_tmp_com_dbg.py', '_tmp_fix_tech.py', '_tmp_patch_ref.py', '_tmp_probe14.py',
                    '_tmp_ref_dbg.py', 'tools_make_icons.py', 'render_pdf_pages.ps1',
                    'smoke_test.py', 'gesture_test.py', 'visual_qa_runner.py',
                    'run_qa.cmd', 'run_qa_pdf.cmd', 'run_qa_pdf.ps1')) {
    Remove-Item -LiteralPath (Join-Path $stage $junk) -Recurse -Force -ErrorAction SilentlyContinue
}

# --------------------------------------------------- 3. встроенная среда
Write-Host '[2/6] встроенная среда runtime\ (копирование)' -ForegroundColor Cyan
Copy-Tree (Join-Path $Root 'runtime') (Join-Path $stage 'runtime')

if ($Profile -eq 'thin') {
    Write-Host '[3/6] урезание неиспользуемого' -ForegroundColor Cyan
    $qt = Join-Path $stage 'runtime\python\Lib\site-packages\PySide6'

    # Модули, которых приложение не касается ни в одном import'е.
    $deadFilePatterns = @(
        'Qt6WebEngine*', 'QtWebEngine*', 'Qt6Quick*', 'QtQuick*', 'Qt6Qml*', 'QtQml*',
        'Qt6Designer*', 'QtDesigner*', 'qt6designer*', 'Qt6Pdf*', 'QtPdf*',
        'Qt6Multimedia*', 'QtMultimedia*', 'avcodec-*', 'avformat-*', 'avutil-*',
        'swresample-*', 'swscale-*', 'Qt6Network*', 'QtNetwork*', 'Qt6Position*',
        'Qt6Sensors*', 'Qt6TextToSpeech*', 'Qt6WebSockets*', 'Qt6VirtualKeyboard*',
        'Qt6SerialPort*', 'Qt6SerialBus*', 'Qt6Bluetooth*', 'Qt6Nfc*', 'Qt6WebChannel*',
        'Qt6WebView*', 'Qt6ShaderTools*', 'Qt6OpenGL*', 'QtOpenGL*', 'Qt63D*',
        'Qt6RemoteObjects*', 'Qt6Scxml*', 'openglsw*', '*.pyi', '*.debug'
    )
    $removed = 0
    foreach ($pattern in $deadFilePatterns) {
        Get-ChildItem -LiteralPath $qt -Recurse -File -Filter $pattern -ErrorAction SilentlyContinue |
            ForEach-Object { Remove-Item $_.FullName -Force; $removed++ }
    }

    # Каталоги сборочного/инструментального назначения и неиспользуемые плагины.
    foreach ($deadDir in @('qml', 'metatypes', 'include', 'typesystems', 'glue', 'scripts',
                           'doc', 'tests', 'support', 'lupdate', 'lrelease')) {
        $p = Join-Path $qt $deadDir
        if (Test-Path $p) { Remove-Item $p -Recurse -Force; $removed++ }
    }
    $keepPlugins = @('platforms', 'styles', 'imageformats', 'iconengines', 'generic', 'textcoders')
    $plug = Join-Path $qt 'plugins'
    if (Test-Path $plug) {
        Get-ChildItem -LiteralPath $plug -Directory | Where-Object { $keepPlugins -notcontains $_.Name } |
            ForEach-Object { Remove-Item $_.FullName -Recurse -Force; $removed++ }
    }

    # WebEngine-ресурсы не нужны; icudtl.dat оставляем (10 МБ, страховка).
    Get-ChildItem -LiteralPath (Join-Path $qt 'resources') -File -Filter '*.pak' -ErrorAction SilentlyContinue |
        ForEach-Object { Remove-Item $_.FullName -Force; $removed++ }

    # Переводы: только ru и en.
    $tr = Join-Path $qt 'translations'
    if (Test-Path $tr) {
        Get-ChildItem -LiteralPath $tr -File | Where-Object {
            $_.Name -notmatch '_(ru|en)\.' -and $_.Name -notmatch '^qtbase_(ru|en)'
        } | ForEach-Object { Remove-Item $_.FullName -Force; $removed++ }
    }

    # Инструменты Qt (designer, uic, rcc, lrelease) в поставке не нужны:
    # приложение не компилирует .ui/.qrc на лету. Удаляем ВСЕ .exe внутри
    # PySide6/shiboken6 — трогать runtime\python\python*.exe это не может,
    # они лежат выше по дереву.
    foreach ($toolDir in @($qt, (Join-Path $stage 'runtime\python\Lib\site-packages\shiboken6'))) {
        Get-ChildItem -Path $toolDir -File -Filter '*.exe' -ErrorAction SilentlyContinue |
            ForEach-Object { Remove-Item $_.FullName -Force; $removed++ }
        Get-ChildItem -Path $toolDir -File -Filter '*.lib' -ErrorAction SilentlyContinue |
            ForEach-Object { Remove-Item $_.FullName -Force; $removed++ }
    }
    # Заголовки C++ нужны только для сборки расширений, не для запуска.
    $shib = Join-Path $stage 'runtime\python\Lib\site-packages\shiboken6'
    if (Test-Path (Join-Path $shib 'include')) {
        Remove-Item (Join-Path $shib 'include') -Recurse -Force; $removed++
    }

    # Инструменты Qt (designer, uic, lrelease) в поставке не нужны.
    Get-ChildItem -LiteralPath (Join-Path $stage 'runtime\python\Scripts') -File -Filter 'pyside6*' -ErrorAction SilentlyContinue |
        ForEach-Object { Remove-Item $_.FullName -Force; $removed++ }

    Write-Host "  удалено позиций: $removed" -ForegroundColor DarkGray
} else {
    Write-Host '[3/6] урезание пропущено (профиль full)' -ForegroundColor DarkGray
}

# --------------------------------------------------- 4. ярлык-установщик
Write-Host '[4/6] установщик ярлыка и памятка' -ForegroundColor Cyan
$shortcutCmd = @'
@echo off
rem Создать ярлык Kuji.lnk на Рабочем столе. Путь берётся отсюда, а не из
rem архива, поэтому поставку можно распаковать в любое место.
chcp 65001 >nul
setlocal
set "APP_DIR=%~dp0"
if not exist "%APP_DIR%Kuji.exe" (
  echo Не найден Kuji.exe рядом с этим файлом. Распакуйте архив целиком.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -Command "$d=[Environment]::GetFolderPath('Desktop'); $l=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $d 'Kuji.lnk')); $l.TargetPath='%APP_DIR%Kuji.exe'; $l.WorkingDirectory='%APP_DIR%'; $l.IconLocation='%APP_DIR%Kuji.exe,0'; $l.Description='Kuji (Куджи) - конструктор логических деревьев событий'; $l.Save()"
if errorlevel 1 (
  echo Не удалось создать ярлык. Можно запускать Kuji.exe двойным кликом прямо отсюда.
) else (
  echo Ярлык Kuji.lnk создан на Рабочем столе.
)
pause
'@
# batch-файл обязан быть БЕЗ BOM: cmd.exe не понимает «﻿@echo off».
[IO.File]::WriteAllText((Join-Path $stage 'Установить ярлык.cmd'), $shortcutCmd,
    (New-Object Text.UTF8Encoding($false)))

$readme = @"
Kuji (Куджи) $version — конструктор логических деревьев событий (Методика МЧС № 533)

КАК ЗАПУСТИТЬ
  1. Распакуйте архив в любую папку (например, D:\Kuji). Вложенность важнее
     расположения: внутри должна остаться структура Kuji.exe + runtime\.
  2. Двойной клик по Kuji.exe. Окно консоли не появляется, приложение
     использует встроенную среду Python из runtime\ — ничего устанавливать
     не нужно, права администратора не нужны.
  3. «Установить ярлык.cmd» — кладёт Kuji.lnk на Рабочий стол.

ЕСЛИ НУЖЕН ЗАПУСК ЧЕРЕЗ КОНСОЛЬ (для диагностики)
  run_app.cmd

ДАННЫЕ
  Настройки и последние пути хранятся в папке settings\ рядом с программой,
  поэтому поставку можно переносить целиком, а пользовательские проекты —
  в любом месте диска.

ПОДРОБНОЕ ОПИСАНИЕ ВОЗМОЖНОСТЕЙ — README.md.
"@
Set-Content -LiteralPath (Join-Path $stage 'КАК ЗАПУСТИТЬ.txt') -Value $readme -Encoding UTF8

# ------------------------------------------------------------- 5. проверка
function Get-Mb([string]$Path) {
    $sum = (Get-ChildItem -LiteralPath $Path -Recurse -File -Force -ErrorAction SilentlyContinue |
        Measure-Object Length -Sum).Sum
    return [math]::Round($sum / 1MB, 1)
}
Write-Host ("  размер папки поставки: {0} МБ" -f (Get-Mb $stage))

if (-not $SkipVerify) {
    Write-Host '[5/6] проверка запуском из собранной папки' -ForegroundColor Cyan
    $stagedExe = Join-Path $stage 'Kuji.exe'
    $before = Get-CimInstance Win32_Process -Filter "Name='pythonw.exe' OR Name='python.exe'" |
        ForEach-Object { $_.ProcessId }
    Start-Process -FilePath $env:WINDIR\System32\cmd.exe `
        -ArgumentList "/c start `"`" /D `"$stage`" `"$stagedExe`"" -WindowStyle Hidden
    Start-Sleep -Seconds 20

    $newProc = Get-CimInstance Win32_Process -Filter "Name='pythonw.exe' OR Name='python.exe'" |
        Where-Object { $before -notcontains $_.ProcessId -and $_.CommandLine -like '*main.py*' }
    if (-not $newProc) {
        throw 'Проверка не пройдена: из собранной папки приложение не запустилось. Архив не выпущен.'
    }
    $procId = @($newProc)[0].ProcessId
    Write-Host "  приложение запустилось (PID $procId)" -ForegroundColor Green
    Start-Sleep -Seconds 5
    if (-not (Get-Process -Id $procId -ErrorAction SilentlyContinue)) {
        throw 'Проверка не пройдена: приложение завершилось сразу после запуска.'
    }
    Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
} else {
    Write-Host '[5/6] проверка запуском пропущена' -ForegroundColor Yellow
}

# ------------------------------------------------- 5.5 очистка следов сборки
# Проверочный запуск ПОСЛЕ шага 5 создаёт в папке поставки пользовательское
# состояние: settings\*.ini (окно, последние папки — геометрия с этой машины
# ушла бы к заказчику), qa_artifacts\startup.log и кэш *.pyc. Всё это выметается
# перед упаковкой: поставка обязана стартовать «чистой», как при первом запуске.
Write-Host '  очистка следов проверочного запуска' -ForegroundColor DarkGray
foreach ($state in @('settings', 'qa_artifacts', 'test_exports', 'data')) {
    Remove-Item -LiteralPath (Join-Path $stage $state) -Recurse -Force -ErrorAction SilentlyContinue
}
Get-ChildItem -LiteralPath $stage -Recurse -Directory -Filter '__pycache__' -ErrorAction SilentlyContinue |
    ForEach-Object { Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue }
# -Include с -LiteralPath не работает (молча ничего не выбирает), поэтому -Filter.
foreach ($mask in @('*.pyc', '*.pyo')) {
    Get-ChildItem -Path $stage -Recurse -File -Filter $mask -ErrorAction SilentlyContinue |
        ForEach-Object { Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue }
}

# ---------------------------------------------------------------- 6. 7z
Write-Host '[6/6] упаковка 7z' -ForegroundColor Cyan
$7z = 'C:\Program Files\7-Zip\7z.exe'
if (-not (Test-Path $7z)) {
    $7z = (Get-Command 7z.exe -ErrorAction SilentlyContinue).Source
    if (-not $7z) { throw 'Не найден 7z.exe. Установите 7-Zip или укажите -SkipVerify и упакуйте вручную.' }
}

New-Item -ItemType Directory -Path $Out -Force | Out-Null
$archive = Join-Path $Out "$baseName.7z"
Remove-Item $archive -Force -ErrorAction SilentlyContinue

& $7z a -t7z -mx=5 -m0=LZMA2 -mfb=256 -md=256m -ms=on -mmt=on "$archive" "$stage\*" |
    Select-Object -Last 6
if ($LASTEXITCODE -gt 2) { throw "7z завершился с кодом $LASTEXITCODE" }

if ($Sfx) {
    $sfxModule = 'C:\Program Files\7-Zip\7z.sfx'
    if (Test-Path $sfxModule) {
        $sfxExe = Join-Path $Out "$baseName.exe"
        $cfg = Join-Path $Out "$baseName.sfx.cfg"
        # BOM здесь убивает конфиг: 7-Zip ищет «;!@Install@!» сразу после
        # SFX-модуля, а EF BB BF перед ним мешает распознать заголовок, и
        # такой exe распаковывается молча, без Title/BeginPrompt/RunProgram.
        # Here-string нельзя вставлять в аргументы метода — сначала переменная.
        $cfgText = @"
;!@Install@!UTF-8!
Title="Kuji $version"
BeginPrompt="Распаковать Kuji $version в эту папку?"
RunProgram="Kuji\\Kuji.exe"
PullDownTitle="Kuji (Куджи)"
"@
        [IO.File]::WriteAllText($cfg, $cfgText, (New-Object Text.UTF8Encoding($false)))
        & $env:WINDIR\System32\cmd.exe /c copy /b "$sfxModule" + "$cfg" + "$archive" "$sfxExe" | Out-Null
        Remove-Item $cfg -Force -ErrorAction SilentlyContinue
        if (Test-Path $sfxExe) { Write-Host ("  SFX: {0}" -f $sfxExe) -ForegroundColor Green }
    } else {
        Write-Host '  SFX-модуль 7-Zip не найден — пропущено' -ForegroundColor Yellow
    }
}

# Размер папки поставки считаем ДО удаления: после -Keep=False считать уже не с чего.
$stageMb = Get-Mb $stage

if (-not $Keep) {
    Remove-Item $stage -Recurse -Force -ErrorAction SilentlyContinue
}

$archMb = [math]::Round((Get-Item $archive).Length / 1MB, 1)
Write-Host ''
Write-Host ("ГОТОВО  {0}`n        {1} МБ (папка поставки: {2} МБ, профиль {3})" -f $archive, $archMb, $stageMb, $Profile) -ForegroundColor Green

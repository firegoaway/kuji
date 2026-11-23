<#
    Сборка поставки Kuji для раздачи: папка, ZIP и 7z-архивы.

    Логика одинакова для обоих профилей: из рабочего дерева выкладывается
    чистая папка dist\Kuji (код + встроенная среда + Kuji.exe + установщик
    ярлыка), она ПРОВЕРЯЕТСЯ запуском, и только потом упаковывается. Архив
    из непроверенной папки не выпускается.

    Профили:
      full  - среда как есть (эталон, ~900 МБ).
      thin  - вырезается то, что приложение не импортирует: WebEngine,
              QML/Quick, Designer, PDF, мультимедиа, Network, *.pyi,
              metatypes/include/typesystems/qml, *.pak, pip, неиспользуемые
              плагины Qt и переводы кроме ru/en. Основание: по всем import
              в eta\ приложению нужны только QtCore / QtGui / QtWidgets /
              QtSvg, плюс pandoc для экспорта DOCX.

    Форматы: по умолчанию both. Главный файл для GitHub Releases - ZIP, его
    раскрывает проводник Windows 10/11 без архиватора; 7z идёт уменьшенной
    копией для медленного канала. Рядом с каждым архивом кладётся .sha256,
    а в dist\Kuji-*-release-notes.md собирается текст описания релиза.

    Ярлык в архив не кладётся как .lnk: .lnk помнит абсолютный путь и после
    распаковки на другой машине указывал бы в никуда. Вместо него летят
    install_shortcut.cmd (чистый ASCII) и make_shortcut.ps1 (русские строки,
    UTF-8 с BOM): ярлык создаётся на месте, от фактического местоположения.
    Разделение по кодировкам обязательно - cmd.exe ломается на кириллице в
    батче, PowerShell 5.1 ломается без BOM. DETAILS: TECHNICAL.md, раздел
    про поставку, ловушки №2 и №2b.

    Запуск:
      powershell -NoProfile -ExecutionPolicy Bypass -File tools\dist\make_dist.ps1
      ... -Profile full        # без урезания среды
      ... -Format zip|7z|both  # что упаковывать (по умолчанию both)
      ... -Sfx                 # дополнительно self-extracting exe-установщик
      ... -SkipVerify          # не запускать собранную папку (только отладка)
      ... -Keep                # не удалять dist\Kuji после упаковки
#>

[CmdletBinding()]
param(
    [ValidateSet('thin', 'full')]
    [string]$Profile = 'thin',

    # Формат выгрузки. Для Releases по умолчанию BOTH: zip обязателен, потому
    # что раскрывается проводником Windows 10/11 без всякого архиватора, а 7z
    # идёт как уменьшенная копия для медленных каналов (требует 7-Zip).
    [ValidateSet('zip', '7z', 'both')]
    [string]$Format = 'both',

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
                 '/XF', '*.pyc', '*.pyo', '*.log', '*.bak', 'Thumbs.db', 'desktop.ini')
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

    # WebEngine-ресурсы не нужны вместе с самим WebEngine. icudtl.dat читает
    # только WebEngine (в Qt6Core ICU вкомпилирован), поэтому в thin он тоже
    # уходит: 13 МБ.
    $res = Join-Path $qt 'resources'
    if (Test-Path $res) {
        Get-ChildItem -LiteralPath $res -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -like '*.pak' -or $_.Name -eq 'icudtl.dat' } |
            ForEach-Object { Remove-Item $_.FullName -Force; $removed++ }
    }

    # Переводы: только ru и en. ОБЯЗАТЕЛЬНО рекурсивно: в PySide6 6.12 внутри
    # translations лежит подкаталог qtwebengine_locales с ~57 *.pak по 1,5 МБ
    # (43 МБ), и без -Recurse он переживал чистку целиком — замер 23.11.2026:
    # 44,2 МБ остатка вместо 0,6 МБ.
    $tr = Join-Path $qt 'translations'
    if (Test-Path $tr) {
        $welo = Join-Path $tr 'qtwebengine_locales'
        if (Test-Path $welo) { Remove-Item $welo -Recurse -Force; $removed++ }
        Get-ChildItem -LiteralPath $tr -Recurse -File -ErrorAction SilentlyContinue | Where-Object {
            $_.Name -notmatch '_(ru|en)\.' -and $_.Name -notmatch '^qtbase_(ru|en)'
        } | ForEach-Object { Remove-Item $_.FullName -Force; $removed++ }
    }

    # pip в поставке не нужен: приложение запускает pythonw с готовым
    # окружением, а установка пакетов на рабочей машине — отдельная
    # санкционированная процедура (offline-колёса), не часть поставки.
    $sp = Join-Path $stage 'runtime\python\Lib\site-packages'
    foreach ($pipDir in @('pip', 'pip-26.3.dist-info')) {
        $p = Join-Path $sp $pipDir
        if (Test-Path $p) { Remove-Item $p -Recurse -Force; $removed++ }
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

# ДВА файла намеренно разделены. .cmd — чистый ASCII: cmd.exe при кириллице в
# файле рассинхронизирует пакетный читатель (переход по байтовым смещениям в
# другой кодовой странице) и начинает ИСПОЛНЯТЬ куски комментариев — проверено
# на build_exe.cmd 23.11.2026. Все русские строки живут в .ps1 с UTF-8 BOM,
# который Windows PowerShell 5.1 читает правильно.
$shortcutCmd = @'
@echo off
rem Create "Kuji.lnk" on the Desktop, pointing at THIS folder.
rem ASCII only on purpose - see make_shortcut.ps1 for the Russian messages.
setlocal
set "APP_DIR=%~dp0"
if not exist "%APP_DIR%Kuji.exe" (
    echo ERROR: Kuji.exe not found next to this file. Extract the whole archive.
    pause
    exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%APP_DIR%make_shortcut.ps1"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
    echo.
    echo Shortcut creation FAILED with exit code %RC%.
    echo You can still start Kuji by double-clicking Kuji.exe in this folder.
)
pause
endlocal
'@
[IO.File]::WriteAllText((Join-Path $stage 'install_shortcut.cmd'), $shortcutCmd,
    (New-Object Text.UTF8Encoding($false)))

$shortcutPs1 = @'
<#
    Создаёт «Kuji.lnk» на Рабочем столе, беря путь ТАМ, где поставка реально
    лежит, а не там, где её упаковывали в архив. Поэтому ярлык можно ставить
    после распаковки в любую папку и на любой диск — он всё равно попадёт в
    своё Kuji.exe. Иконка берётся из самого exe, она вшита при сборке.
#>
[CmdletBinding()]
param(
    # Каталог приложения; по умолчанию — тот, где лежит этот скрипт.
    [string]$AppDir = '',

    # Куда класть ярлык; по умолчанию — Рабочий стол текущего пользователя.
    [string]$LnkFolder = ''
)

$ErrorActionPreference = 'Stop'

if (-not $AppDir) { $AppDir = Split-Path -Parent $MyInvocation.MyCommand.Path }
if (-not $LnkFolder) { $LnkFolder = [Environment]::GetFolderPath('Desktop') }

$exe = Join-Path $AppDir 'Kuji.exe'
if (-not (Test-Path $exe)) {
    Write-Host "Не найден Kuji.exe в папке: $AppDir" -ForegroundColor Red
    Write-Host 'Распакуйте архив целиком, не выбирая отдельные файлы.' -ForegroundColor Yellow
    exit 1
}

New-Item -ItemType Directory -Path $LnkFolder -Force | Out-Null
$lnkPath = Join-Path $LnkFolder 'Kuji.lnk'

$shell = New-Object -ComObject WScript.Shell
$lnk = $shell.CreateShortcut($lnkPath)
$lnk.TargetPath = $exe
# Рабочий каталог обязателен: приложение ищет settings\ и runtime\ от корня.
$lnk.WorkingDirectory = $AppDir
$lnk.IconLocation = "$exe,0"
$lnk.Description = 'Kuji (Куджи) — конструктор логических деревьев событий'
$lnk.Save()

Write-Host "Ярлык создан: $lnkPath" -ForegroundColor Green
Write-Host 'Запуск — двойной клик по значку Kuji на Рабочем столе.' -ForegroundColor Cyan
exit 0
'@
# .ps1 с кириллицей обязан быть UTF-8 С BOM, иначе PowerShell 5.1 прочитает
# его как ANSI и русский текст развалится на синтаксические токены.
[IO.File]::WriteAllText((Join-Path $stage 'make_shortcut.ps1'), $shortcutPs1,
    (New-Object Text.UTF8Encoding($true)))

$readme = @"
Kuji (Куджи) $version — конструктор логических деревьев событий (Методика МЧС № 533)

КАК ЗАПУСТИТЬ
  1. Распакуйте архив в любую папку (например, D:\Kuji). Вложенность важнее
     расположения: внутри должна остаться структура Kuji.exe + runtime\.
  2. Двойной клик по Kuji.exe. Окно консоли не появляется, приложение
     использует встроенную среду Python из runtime\ — ничего устанавливать
     не нужно, права администратора не нужны.
  3. «install_shortcut.cmd» — кладёт ярлык Kuji.lnk на Рабочий стол.
     Сам .lnk в архив не кладётся намеренно: он помнит абсолютный путь и
     после распаковки на другой машине указывал бы в никуда.

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
foreach ($mask in @('*.pyc', '*.pyo', '*.bak')) {
    Get-ChildItem -Path $stage -Recurse -File -Filter $mask -ErrorAction SilentlyContinue |
        ForEach-Object { Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue }
}

# ------------------------------------------------------- 6. упаковка и хэши
Write-Host '[6/6] упаковка' -ForegroundColor Cyan
$7z = 'C:\Program Files\7-Zip\7z.exe'
if (-not (Test-Path $7z)) {
    $7z = (Get-Command 7z.exe -ErrorAction SilentlyContinue).Source
    if (-not $7z) { throw 'Не найден 7z.exe — без него поставка не упаковывается.' }
}

New-Item -ItemType Directory -Path $Out -Force | Out-Null

# Один файло вложении GitHub Releases весит не больше 100 МБ, поэтому размер
# проверяется здесь и кричит здесь, а не на сайте при загрузке.
$capMb = 100

$pack = @()
if ($Format -in @('zip', 'both')) {
    $pack += [pscustomobject]@{ Ext = 'zip';sevenZ = $false
        # -mcu ОБЯЗАТЕЛЕН: без него 7-Zip пишет имена записей zip в OEM-странице
        # и НЕ взводит UTF-8 флаг (bit 11), из-за чего «КАК ЗАПУСТИТЬ.txt»
        # распаковывается в «ЉЂЉ ‡ЂЏ“‘’€’њ.txt» — проводник Windows читает такое
        # имя как CP437. Замер 23.11.2026: с -mcu [IO.Compression.ZipFile]
        # отдаёт корректное кириллическое имя, без -mcu — кашу.
        Args = @('-tzip', '-mx=9', '-mm=Deflate', '-mfb=256', '-mcu')
        Why  = 'открывается проводником Windows 10/11 без архиватора — основной файл Releases' }
}
if ($Format -in @('7z', 'both')) {
    $pack += [pscustomobject]@{ Ext = '7z';sevenZ = $true
        Args = @('-t7z', '-mx=5', '-m0=LZMA2', '-mfb=256', '-md=256m', '-ms=on')
        Why  = 'меньше размером, но требует 7-Zip — запасной файл для медленного канала' }
}

$artifacts = @()
$sevenZArchive = $null
foreach ($p in $pack) {
    $archive = Join-Path $Out ('{0}.{1}' -f $baseName, $p.Ext)
    Remove-Item $archive -Force -ErrorAction SilentlyContinue
    # Пакуем САМУ папку, а не её содержимое: в архиве всё лежит внутри Kuji\,
    # поэтому «Извлечь всё» в проводнике создаёт одну аккуратную папку, а не
    # высыпает десяток объектов в текущую, и путь RunProgram="Kuji\Kuji.exe"
    # у SFX-установщика оказывается верным.
    & $7z a $p.Args $archive $stage | Select-Object -Last 3
    if ($LASTEXITCODE -gt 2) { throw ("7z ({0}) завершился с кодом {1}" -f $p.Ext, $LASTEXITCODE) }
    if ($p.sevenZ) { $sevenZArchive = $archive }

    $leaf = Split-Path -Leaf $archive
    $mb = [math]::Round((Get-Item $archive).Length / 1MB, 1)
    $sha = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLower()
    # Рядом кладётся .sha256 — инженер сверяет файл, не скачивая ни у кого эталон.
    [IO.File]::WriteAllText("$archive.sha256.txt", ('{0}  {1}' -f $sha, $leaf),
        (New-Object Text.UTF8Encoding($false)))

    $artifacts += [pscustomobject]@{ File = $leaf; MB = $mb; SHA256 = $sha; Note = $p.Why }
    $color = if ($mb -gt $capMb) { 'Yellow' } else { 'Green' }
    Write-Host ("  {0}  {1} МБ{2}" -f $leaf, $mb,
        $(if ($mb -gt $capMb) { '  !!! БОЛЬШЕ ЛИМИТА GITHUB (100 МБ)' } else { '' })) -ForegroundColor $color
}

# SFX: двойной клик = распаковка + запуск. Полезна как «установщик одним
# файлом», но иконка у неё системная 7-Zip, а не Kuji, поэтому в Releases
# основным идёт zip.
if ($Sfx -and $sevenZArchive) {
    $sfxModule = 'C:\Program Files\7-Zip\7z.sfx'
    if (Test-Path $sfxModule) {
        $sfxExe = Join-Path $Out "$baseName-setup.exe"
        $cfg = Join-Path $Out "$baseName.sfx.cfg"
        # BOM здесь убивает конфиг: 7-Zip ищет «;!@Install@!» сразу после
        # SFX-модуля, а EF BB BF перед ним мешает распознать заголовок, и
        # такой exe распаковывается молча, без Title/BeginPrompt/RunProgram.
        # Here-string нельзя вставлять в аргументы метода — сначала переменная.
        $cfgText = @"
;!@Install@!UTF-8!
Title="Kuji $version"
BeginPrompt="Установить Kuji $version в эту папку?"
RunProgram="Kuji\\Kuji.exe"
PullDownTitle="Kuji (Куджи)"
"@
        [IO.File]::WriteAllText($cfg, $cfgText, (New-Object Text.UTF8Encoding($false)))
        & $env:WINDIR\System32\cmd.exe /c copy /b "$sfxModule" + "$cfg" + "$sevenZArchive" "$sfxExe" | Out-Null
        Remove-Item $cfg -Force -ErrorAction SilentlyContinue
        if (Test-Path $sfxExe) {
            $sfxMb = [math]::Round((Get-Item $sfxExe).Length / 1MB, 1)
            $sfxSha = (Get-FileHash -LiteralPath $sfxExe -Algorithm SHA256).Hash.ToLower()
            [IO.File]::WriteAllText("$sfxExe.sha256.txt", ('{0}  {1}' -f $sfxSha, (Split-Path -Leaf $sfxExe)),
                (New-Object Text.UTF8Encoding($false)))
            $artifacts += [pscustomobject]@{ File = (Split-Path -Leaf $sfxExe); MB = $sfxMb; SHA256 = $sfxSha
                Note = 'распаковка и запуск двойным кликом; иконка — системная 7-Zip' }
            Write-Host ("  {0}  {1} МБ" -f (Split-Path -Leaf $sfxExe), $sfxMb) -ForegroundColor Green
        }
    } else {
        Write-Host '  SFX-модуль 7-Zip не найден — пропущено' -ForegroundColor Yellow
    }
}

# ------------------------------------------- текст для страницы Releases.md
$artTable = ($artifacts | ForEach-Object { '| `{0}` | {1} |' -f $_.File, $_.MB }) -join "`n"
$shaBlock = ($artifacts | ForEach-Object { '{0}  {1}' -f $_.SHA256, $_.File }) -join "`n"
$tick = [char]0x60        # бэктик отдельной переменной: в double-quoted
$fence = ([string]$tick) * 3   # here-string он ещё и символ экранирования.
                              # УМНОЖАТЬ НАДО string, а не char: [char]*3 не
                              # определён и роняет скрипт ([System.Char] *
                              # [System.Int32] is not defined).

# Главный файл в описании релиза — тот, что раскрывается без архиватора.
$zipArtifact = @($artifacts | Where-Object { $_.File -like '*.zip' })
$primary = if ($zipArtifact.Count) { $zipArtifact[0].File } else { $artifacts[0].File }

$notes = @"
## Kuji (Куджи) $version — готовая программа для Windows 10 и 11 (64 бит)

Скачайте **$primary**, распакуйте в любую папку (например, ${tick}D:\Kuji${tick}) и запустите двойным кликом **Kuji.exe**. Ничего дополнительно устанавливать не нужно: среда выполнения Python и библиотеки Qt встроены в папку, права администратора не требуются. ZIP раскрывается штатными средствами Windows, архиватор не нужен.

| файл | размер, МБ |
|---|---|
$artTable

### Что нужно знать перед первым запуском

- Работает на Windows 10 и Windows 11, 64 бита. Горячие клавиши одинаково действуют и в английской, и в русской раскладке.
- SmartScreen и антивирус могут сообщить, что издатель программы неизвестен: сборка не подписана коммерческим сертификатом. Для внутренней инженерной программы это нормально; при необходимости добавьте папку в исключения.
- Отчёт DOCX собирается встроенным конвертером, и Microsoft Word для его создания не нужен. Word понадобится только чтобы открыть готовый файл.
- Настройки лежат в папке ${tick}settings${tick} рядом с программой, поэтому всё рабочее место переносится вместе с папкой.
- Ярлык на Рабочем столе создаёт ${tick}install_shortcut.cmd${tick} из той же папки; без него программа запускается двойным кликом по ${tick}Kuji.exe${tick}.

### Проверка целостности (SHA-256)

${fence}
$shaBlock
${fence}
"@


$notesPath = Join-Path $Out "$baseName-release-notes.md"
[IO.File]::WriteAllText($notesPath, $notes, (New-Object Text.UTF8Encoding($false)))
Write-Host ("  текст для Releases: {0}" -f (Split-Path -Leaf $notesPath)) -ForegroundColor DarkGray

# Размер папки поставки считаем ДО удаления: после -Keep=False считать уже не с чего.
$stageMb = Get-Mb $stage
if (-not $Keep) {
    Remove-Item $stage -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host ''
Write-Host ("ГОТОВО  профиль {0}: папка {1} МБ" -f $Profile, $stageMb) -ForegroundColor Green
$artifacts | Format-Table File, MB, Note -AutoSize | Out-String -Width 140 | Write-Host

<#
    Публикация релиза Kuji на GitHub Releases.

    Пара к tools\dist\make_dist.ps1: тот собирает и проверяет архивы, этот
    поднимает их под уже существующий тег. Разделение намеренное: сборка
    работает офлайн и без сети, а публикация требует интернета и учётной
    записи.

    Что нужно заранее:
      1. make_dist.ps1 отработал (в dist\ лежат zip, 7z, setup.exe, .sha256.txt
         и Kuji-<версия>-release-notes.md);
      2. тег v<версия> создан и ОТПУШЕН (без тега GitHub отвечает 422).

    Запуск:
      powershell -NoProfile -ExecutionPolicy Bypass -File tools\dist\publish_release.ps1 -DryRun
      powershell -NoProfile -ExecutionPolicy Bypass -File tools\dist\publish_release.ps1

    Токен берётся из Windows Credential Manager той же учётной записи, которой
    вы пушите git (git credential fill). Он живёт только в переменной этого
    процесса: не печатается, не пишется на диск, временные файлы запроса
    удаляются в finally. Альтернатива - переменная окружения GITHUB_TOKEN или
    GH_TOKEN (например, fine-grained PAT с доступом только на этот репозиторий
    и правом contents: write).

    ВАЖНО про кодировки: тело запроса уходит байтами UTF-8, иначе PowerShell
    5.1 испортит кириллицу в названии и описании релиза. Файл с русскими
    комментариями обязан быть UTF-8 с BOM.
#>

[CmdletBinding()]
param(
    [string]$Root = '',
    [string]$Owner = 'firegoaway',
    [string]$Repo = 'kuji',

    # Тег релиза; по умолчанию v<версия из eta\__init__.py>.
    [string]$Tag = '',

    # Заголовок страницы Releases.
    [string]$Title = '',

    # Только проверить всё и показать, что будет сделано.
    [switch]$DryRun,

    # Не перезакачивать ассеты (обновить лишь текст релиза).
    [switch]$TextOnly
)

$ErrorActionPreference = 'Stop'

if (-not $Root) {
    $Root = (Get-Item $PSScriptRoot).Parent.Parent.FullName
}
$distDir = Join-Path $Root 'dist'

# ------------------------------------------------------------- версия/тег
$verLine = Select-String -Path (Join-Path $Root 'eta\__init__.py') -Pattern '__version__\s*=\s*"([^"]+)"' |
    Select-Object -First 1
if (-not $verLine) { throw 'Не найдена версия в eta\__init__.py' }
$version = $verLine.Matches[0].Groups[1].Value
if (-not $Tag) { $Tag = "v$version" }
if (-not $Title) { $Title = "Kuji (Куджи) $version — готовая программа для Windows" }

Write-Host "Kuji $version | тег $Tag | $Owner/$Repo" -ForegroundColor Cyan

# ------------------------------------------------------------ артефакты
$baseName = "Kuji-$version-win64"
$notesFile = Join-Path $distDir "$baseName-release-notes.md"
if (-not (Test-Path $notesFile)) {
    throw "Нет текста релиза: $notesFile — сначала выполните make_dist.ps1"
}

$assets = @()
foreach ($pattern in @("$baseName.zip", "$baseName.7z", "$baseName-setup.exe")) {
    $f = Get-ChildItem $distDir -Filter $pattern -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($f) { $assets += $f }
}
if (-not $assets) { throw "В $distDir нет ни одного архива — сначала make_dist.ps1" }

foreach ($a in $assets) {
    $shaFile = "$($a.FullName).sha256.txt"
    if (-not (Test-Path $shaFile)) {
        # Хэш считаем на месте, если рядом его нет: без него страница релиза
        # теряет смысл проверки загрузки.
        $hash = (Get-FileHash -LiteralPath $a.FullName -Algorithm SHA256).Hash.ToLower()
        [IO.File]::WriteAllText($shaFile, ('{0}  {1}' -f $hash, $a.Name),
            (New-Object Text.UTF8Encoding($false)))
    }
}
$shaFiles = @(Get-ChildItem $distDir -Filter '*.sha256.txt' -ErrorAction SilentlyContinue)

Write-Host '  артефакты:' -ForegroundColor DarkGray
foreach ($a in $assets) {
    $mb = [math]::Round($a.Length / 1MB, 1)
    $cap = if ($mb -gt 100) { '  !!! больше лимита GitHub 100 МБ' } else { '' }
    Write-Host ("    {0,-34} {1,7} МБ{2}" -f $a.Name, $mb, $cap) -ForegroundColor DarkGray
}

# ------------------------------------------------------------------ токены
$token = $env:GITHUB_TOKEN
if (-not $token) { $token = $env:GH_TOKEN }
if ($token) {
    Write-Host '  токен взят из переменной окружения' -ForegroundColor DarkGray
} else {
    $nl = [char]10
    $reqFile = Join-Path $env:TEMP 'kuji_gcreq.txt'
    $outFile = Join-Path $env:TEMP 'kuji_gcout.txt'
    try {
        [IO.File]::WriteAllText($reqFile, ('protocol=https' + $nl + 'host=github.com' + $nl + $nl))
        & cmd.exe /c ('git credential fill < "' + $reqFile + '" > "' + $outFile + '" 2>nul') | Out-Null
        $lines = @()
        if (Test-Path $outFile) { $lines = [IO.File]::ReadAllLines($outFile) }
        $passLine = $lines | Where-Object { $_ -like 'password=*' } | Select-Object -First 1
        if ($passLine) { $token = $passLine.Substring(9).Trim() }
    }
    finally {
        Remove-Item $reqFile, $outFile -Force -ErrorAction SilentlyContinue
    }
    if ($token) {
        Write-Host ('  токен взят из Credential Manager (длина ' + $token.Length + ')') -ForegroundColor DarkGray
    } else {
        throw @'
Не найден токен GitHub.
  Вариант 1: выполните любой `git push` в терминале и войдите через браузер -
             запись появится в Credential Manager, после этого этот скрипт
             заработает сам.
  Вариант 2: создайте fine-grained personal access token (доступ только к этому
             репозиторию, право contents: write) и задайте переменную
             окружения GITHUB_TOKEN.
'@
    }
}

$api = "https://api.github.com/repos/$Owner/$Repo"
$hdr = @{
    Authorization = "Bearer $token"
    Accept        = 'application/vnd.github+json'
    'User-Agent'  = 'kuji-publish-release'
}

# ------------------------------------------------------- проверки до записи
$rInfo = Invoke-RestMethod -Uri $api -Headers $hdr -TimeoutSec 60
Write-Host ("  репозиторий: {0} (ветка по умолчанию {1})" -f $rInfo.full_name, $rInfo.default_branch)

try {
    $ref = Invoke-RestMethod -Uri "$api/git/ref/tags/$Tag" -Headers $hdr -TimeoutSec 60
    Write-Host ("  тег на сервере: {0} -> {1}" -f $Tag, $ref.object.sha.Substring(0, 8)) -ForegroundColor Green
} catch {
    throw "Тега $Tag на GitHub нет. Создайте и отправьте: git tag -a $Tag -F msg.txt && git push origin $Tag"
}

$bodyText = [IO.File]::ReadAllText($notesFile, (New-Object Text.UTF8Encoding($false)))
Write-Host ("  текст релиза: {0} симв." -f $bodyText.Length)

if ($DryRun) {
    Write-Host ''
    Write-Host 'DRY RUN — ничего не изменено' -ForegroundColor Yellow
    Write-Host ("    релиз для тега {0}, заголовок: {1}" -f $Tag, $Title)
    $srvRels = Invoke-RestMethod -Uri "$api/releases" -Headers $hdr -TimeoutSec 60
    $srvRel = $srvRels | Where-Object { $_.tag_name -eq $Tag } | Select-Object -First 1
    $onServer = @{}
    if ($srvRel) {
        Write-Host ("    на сервере уже есть релиз id {0} с {1} ассетами" -f $srvRel.id, $srvRel.assets.Count)
        foreach ($a in $srvRel.assets) { $onServer[$a.name] = $true }
    } else {
        Write-Host '    релиза под этим тегом ещё нет — будет создан'
    }
    foreach ($f in (@($assets) + $shaFiles)) {
        $mark = if ($onServer.ContainsKey($f.Name)) { 'уже загружен — будет пропущен' } else { 'закачать' }
        Write-Host ('    {0,-34} {1}' -f $f.Name, $mark)
    }
    return
}

# ------------------------------------------------------ создание/обновление
$payload = ([ordered]@{
    tag_name   = $Tag
    name       = $Title
    body       = $bodyText
    draft      = $false
    prerelease = $false
} | ConvertTo-Json -Depth 5)

# Байты UTF-8 обязательны: строковое тело PowerShell 5.1 передаёт не в UTF-8,
# и кириллица в заголовке/описании превращается в вопросительные знаки.
$payloadBytes = (New-Object Text.UTF8Encoding($false)).GetBytes($payload)

$existing = Invoke-RestMethod -Uri "$api/releases" -Headers $hdr -TimeoutSec 60
$rel = $existing | Where-Object { $_.tag_name -eq $Tag } | Select-Object -First 1
if ($rel) {
    Write-Host ("  релиз уже есть (id {0}) — обновляю текст" -f $rel.id)
    $rel = Invoke-RestMethod -Method Patch -Uri "$api/releases/$($rel.id)" -Headers $hdr `
        -ContentType 'application/json; charset=utf-8' -Body $payloadBytes -TimeoutSec 180
} else {
    Write-Host '  создаю релиз'
    $rel = Invoke-RestMethod -Method Post -Uri "$api/releases" -Headers $hdr `
        -ContentType 'application/json; charset=utf-8' -Body $payloadBytes -TimeoutSec 180
}

# ----------------------------------------------------------------- загрузка
$have = @{}
foreach ($a in $rel.assets) { $have[$a.name] = $true }

if (-not $TextOnly) {
    foreach ($f in (@($assets) + $shaFiles)) {
        $name = $f.Name
        if ($have.ContainsKey($name)) {
            Write-Host ("    есть, пропускаю: {0}" -f $name) -ForegroundColor DarkGray
            continue
        }
        $mb = [math]::Round($f.Length / 1MB, 1)
        Write-Host ("    закаливаю {0} ({1} МБ)..." -f $name, $mb)
        $url = 'https://uploads.github.com/repos/{0}/{1}/releases/{2}/assets?name={3}' -f
            $Owner, $Repo, $rel.id, [Uri]::EscapeDataString($name)
        $up = Invoke-RestMethod -Method Post -Uri $url -Headers $hdr `
            -ContentType 'application/octet-stream' -InFile $f.FullName -TimeoutSec 1800
        if ($up.state -ne 'uploaded') { throw "Ассет $name в состоянии $($up.state)" }
        Write-Host ("    ok: {0}" -f $name) -ForegroundColor Green
    }
}

# ------------------------------------------------------------------ итог
$final = Invoke-RestMethod -Uri "$api/releases/$($rel.id)" -Headers $hdr -TimeoutSec 60
Write-Host ''
Write-Host ('РЕЛИЗ      ' + $final.html_url) -ForegroundColor Green
Write-Host ('СТРАНИЦА   ' + "$($final.html_url)`#release-files") -ForegroundColor Green
foreach ($a in $final.assets) {
    Write-Host ('   {0,-34} {1,7:N1} МБ' -f $a.name, ($a.size / 1MB))
}

param(
    [Parameter(Mandatory = $true)][string]$Pdf,
    [Parameter(Mandatory = $true)][string]$OutPrefix,
    [int[]]$Pages = @(0)
)
# Рендер страниц PDF в PNG (qa_docx_*) через WinRT Windows.Data.Pdf –
# встроенный рендерер Windows, БЕЗ внешних установок. QtPdf (PySide6)
# растеризует некоторые PDF Microsoft Word ЧЕРНЫМИ страницами
# (замер сессии 18), Windows.Data.Pdf справляется. Номера страниц –
# от нуля; имена выходов: <OutPrefix><N+1>.png (в каталоге PDF).
$ErrorActionPreference = "Stop"
Write-Output "RENDER-START"
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Data.Pdf.PdfDocument, Windows.Data.Pdf, ContentType = WindowsRuntime]
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Storage.Streams.IRandomAccessStream, Windows.Storage.Streams, ContentType = WindowsRuntime]
$null = [Windows.Foundation.IAsyncAction, Windows.Foundation, ContentType = WindowsRuntime]

$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() |
    Where-Object { $_.Name -eq "AsTask" -and $_.GetParameters().Count -eq 1 -and
        $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
$asTaskAction = ([System.WindowsRuntimeSystemExtensions].GetMethods() |
    Where-Object { $_.Name -eq "AsTask" -and $_.GetParameters().Count -eq 1 -and
        $_.GetParameters()[0].ParameterType.Name -eq "IAsyncAction" })[0]

function Await($Op, $T) {
    $t = $asTaskGeneric.MakeGenericMethod($T).Invoke($null, @($Op))
    $t.Wait(-1) | Out-Null
    return $t.Result
}

function AwaitAction($Op) {
    $t = $asTaskAction.Invoke($null, @($Op))
    $t.Wait(-1) | Out-Null
}

$pdfFile = Get-Item -LiteralPath $Pdf
$folder = Await ([Windows.Storage.StorageFolder]::GetFolderFromPathAsync(
    $pdfFile.DirectoryName)) ([Windows.Storage.StorageFolder])
$storage = Await ($folder.GetFileAsync($pdfFile.Name)) `
    ([Windows.Storage.StorageFile])
$pdfDoc = Await ([Windows.Data.Pdf.PdfDocument]::LoadFromFileAsync($storage)) `
    ([Windows.Data.Pdf.PdfDocument])

foreach ($p in $Pages) {
    if ($p -lt 0 -or $p -ge $pdfDoc.PageCount) { continue }
    $page = $pdfDoc.GetPage([uint32]$p)
    $name = "{0}{1}.png" -f $OutPrefix, ($p + 1)
    $out = Await ($folder.CreateFileAsync($name,
        [Windows.Storage.CreationCollisionOption]::ReplaceExisting)) `
        ([Windows.Storage.StorageFile])
    $stream = Await ($out.OpenAsync(
        [Windows.Storage.FileAccessMode]::ReadWrite)) `
        ([Windows.Storage.Streams.IRandomAccessStream])
    $opts = New-Object Windows.Data.Pdf.PdfPageRenderOptions
    $opts.DestinationWidth = [uint32]1190
    AwaitAction ($page.RenderToStreamAsync($stream, $opts))
    $stream.Dispose()
    $page.Dispose()
    Write-Output $name
}
# PdfDocument реализует IClosable, но PowerShell не выставляет Dispose –
# сборщик закроет сам; страницы закрыты явно выше

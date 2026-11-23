@echo off
rem =====================================================================
rem  Kuji launcher build (offline, no Visual Studio, no pip, no network)
rem =====================================================================
rem  Uses the C# compiler that ships with Windows (.NET Framework csc.exe)
rem  to compile tools\launcher\KujiLauncher.cs into Kuji.exe in the project
rem  root. The application icon is embedded from assets\icon.ico.
rem
rem  Usage:
rem      build_exe.cmd                 build Kuji.exe only
rem      build_exe.cmd -Shortcut       also place Kuji.lnk on the Desktop
rem
rem  IMPORTANT - this file is deliberately pure ASCII. A .cmd with Cyrillic
rem  text parsed by cmd.exe desynchronizes the batch reader (it re-seeks the
rem  file by byte offsets computed in the previous codepage) and starts
rem  EXECUTING fragments of comment lines. All Russian messages therefore
rem  live in tools\launcher\build_exe.ps1, saved UTF-8 WITH BOM, which
rem  Windows PowerShell 5.1 reads correctly.

setlocal
set "APP_DIR=%~dp0"

where powershell.exe >nul 2>nul
if errorlevel 1 (
    echo ERROR: powershell.exe not found.
    pause
    exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%APP_DIR%tools\launcher\build_exe.ps1" %*
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
    echo.
    echo Build FAILED with exit code %RC%. See the message above.
    pause
    exit /b %RC%
)

echo.
pause
endlocal

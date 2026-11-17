@echo off
rem Headless Visual QA: window / viewport / document view / PDF, no GUI
setlocal
set APP_DIR=%~dp0
set QT_QPA_PLATFORM=offscreen
set QT_QPA_FONTDIR=C:\Windows\Fonts
"%APP_DIR%runtime\python\python.exe" "%APP_DIR%visual_qa_runner.py" %*
endlocal

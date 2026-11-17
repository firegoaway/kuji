@echo off
rem Запуск приложения из автономного embed-окружения runtime\python
setlocal
set APP_DIR=%~dp0
"%APP_DIR%runtime\python\python.exe" "%APP_DIR%main.py" %*
endlocal

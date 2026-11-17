@echo off
rem Задача 2 (сессия 18): диагностический запуск – KUJI_DEBUG_KEYS=1
rem заставляет приложение писать доставку клавиш в qa_artifacts\key_debug.log
setlocal
set APP_DIR=%~dp0
set KUJI_DEBUG_KEYS=1
"%APP_DIR%runtime\python\python.exe" "%APP_DIR%main.py" %*
endlocal

@echo off
setlocal
cd /d "%~dp0"

set "GIT=git"
where git >nul 2>nul || set "GIT=C:\Program Files\Microsoft Visual Studio\18\Enterprise\Common7\IDE\CommonExtensions\Microsoft\TeamFoundation\Team Explorer\Git\cmd\git.exe"

set "MSG=%*"
if "%MSG%"=="" set /p "MSG=Messaggio di commit: "
if "%MSG%"=="" set "MSG=Aggiornamento"

"%GIT%" add -A
"%GIT%" commit -m "%MSG%"
"%GIT%" push origin main

echo.
"%GIT%" status -sb
pause

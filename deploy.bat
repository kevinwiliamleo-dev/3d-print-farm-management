@echo off
:: ============================================================
:: DEPLOY SCRIPT - 3D Print Farm Management
:: Deploy ke Portainer server 192.168.4.67
::
:: PERINTAH:
::   deploy.bat              → Deploy kode terbaru ke server
::   deploy.bat logs         → Lihat logs backend
::   deploy.bat restart      → Restart semua container
::   deploy.bat status       → Cek status container
::   deploy.bat setup        → Panduan setup awal
::   deploy.bat setupghcr    → Daftarkan GHCR registry ke Portainer (wajib sekali)
:: ============================================================

if "%1"=="logs"       goto :logs
if "%1"=="restart"    goto :restart
if "%1"=="status"     goto :status
if "%1"=="setup"      goto :setup
if "%1"=="setupghcr"  goto :setupghcr
goto :deploy

:deploy
powershell -ExecutionPolicy Bypass -File "%~dp0deploy.ps1"
goto :end

:logs
powershell -ExecutionPolicy Bypass -File "%~dp0deploy.ps1" -Logs
goto :end

:restart
powershell -ExecutionPolicy Bypass -File "%~dp0deploy.ps1" -Restart
goto :end

:status
powershell -ExecutionPolicy Bypass -File "%~dp0deploy.ps1" -Status
goto :end

:setup
powershell -ExecutionPolicy Bypass -File "%~dp0deploy.ps1" -Setup
goto :end

:setupghcr
powershell -ExecutionPolicy Bypass -File "%~dp0deploy.ps1" -SetupGHCR
goto :end

:end
pause

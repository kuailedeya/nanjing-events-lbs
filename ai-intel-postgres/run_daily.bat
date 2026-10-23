@echo off
setlocal
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
if not exist logs mkdir logs

set PYTHON_BIN=python
if exist "C:\ProgramData\anaconda3\python.exe" set PYTHON_BIN=C:\ProgramData\anaconda3\python.exe

echo [%date% %time%] daily job start >> logs\daily_wool.log

docker info >nul 2>&1
if errorlevel 1 (
  if exist "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" (
    start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
  )
  for /l %%i in (1,1,60) do (
    docker info >nul 2>&1 && goto docker_ready
    ping -n 3 127.0.0.1 >nul
  )
)
:docker_ready
docker start ai-intel-postgres >nul 2>&1
ping -n 6 127.0.0.1 >nul

%PYTHON_BIN% daily_wool_job.py --target 50000 --workers 8 >> logs\daily_wool.log 2>&1
if errorlevel 1 (
  echo [%date% %time%] harvest failed; skip promotion >> logs\daily_wool.log
) else (
  %PYTHON_BIN% promote_candidates.py --limit 20 >> logs\daily_wool.log 2>&1
)
%PYTHON_BIN% sync_to_postgres.py >> logs\daily_wool.log 2>&1

echo [%date% %time%] daily job done >> logs\daily_wool.log
endlocal

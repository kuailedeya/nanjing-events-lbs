@echo off
setlocal
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d E:\usage\ai-intel-postgres
if not exist logs mkdir logs

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

C:\ProgramData\anaconda3\python.exe daily_wool_job.py --target 50000 --workers 8 >> logs\daily_wool.log 2>&1
if errorlevel 1 (
  echo [%date% %time%] harvest failed; skip promotion >> logs\daily_wool.log
) else (
  C:\ProgramData\anaconda3\python.exe promote_candidates.py --limit 20 >> logs\daily_wool.log 2>&1
)
C:\ProgramData\anaconda3\python.exe sync_to_postgres.py >> logs\daily_wool.log 2>&1

echo [%date% %time%] daily job done >> logs\daily_wool.log
endlocal

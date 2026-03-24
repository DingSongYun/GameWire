@echo off
REM GameWire 数据库备份脚本
REM 用法: scripts\backup.bat [备份目录]

set BACKUP_DIR=%1
if "%BACKUP_DIR%"=="" set BACKUP_DIR=.\backups

set TIMESTAMP=%DATE:~0,4%%DATE:~5,2%%DATE:~8,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set BACKUP_FILE=%BACKUP_DIR%\gamewire_%TIMESTAMP%.sql

if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

echo [GameWire] 正在备份数据库...
docker compose exec -T postgres pg_dump -U gamewire gamewire > "%BACKUP_FILE%"

if %ERRORLEVEL% EQU 0 (
    echo [GameWire] 备份成功: %BACKUP_FILE%
) else (
    echo [GameWire] 备份失败!
    exit /b 1
)

REM 清理 7 天前的备份
forfiles /P "%BACKUP_DIR%" /M "gamewire_*.sql" /D -7 /C "cmd /c del @file" 2>nul
echo [GameWire] 已清理 7 天前的旧备份

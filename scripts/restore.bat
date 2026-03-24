@echo off
REM GameWire 数据库恢复脚本
REM 用法: scripts\restore.bat <备份文件路径>

set BACKUP_FILE=%1
if "%BACKUP_FILE%"=="" (
    echo 用法: scripts\restore.bat ^<备份文件路径^>
    echo 示例: scripts\restore.bat backups\gamewire_20240115_100000.sql
    exit /b 1
)

if not exist "%BACKUP_FILE%" (
    echo [GameWire] 错误: 备份文件不存在: %BACKUP_FILE%
    exit /b 1
)

echo [GameWire] 警告: 这将覆盖现有数据库!
set /p CONFIRM=确认恢复? (y/N): 
if /i not "%CONFIRM%"=="y" (
    echo [GameWire] 已取消
    exit /b 0
)

echo [GameWire] 正在恢复数据库...
docker compose exec -T postgres psql -U gamewire -d gamewire < "%BACKUP_FILE%"

if %ERRORLEVEL% EQU 0 (
    echo [GameWire] 恢复成功!
) else (
    echo [GameWire] 恢复失败!
    exit /b 1
)

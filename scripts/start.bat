@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM ============================================
REM  GameWire 一键启动脚本 (Windows)
REM  用法: scripts\start.bat [--rebuild] [--stop]
REM ============================================

set "PROJECT_ROOT=%~dp0.."
cd /d "%PROJECT_ROOT%"

set "BLUE=[94m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "RESET=[0m"
set "BOLD=[1m"

echo.
echo %BLUE%%BOLD%=========================================%RESET%
echo %BLUE%%BOLD%  🎮 GameWire - 游戏行业资讯聚合平台     %RESET%
echo %BLUE%%BOLD%=========================================%RESET%
echo.

REM ---- 处理命令行参数 ----
if "%1"=="--stop" goto :stop_services
if "%1"=="--rebuild" set "REBUILD=1"

REM ---- Step 1: 检查 Docker ----
echo %YELLOW%[1/6]%RESET% 检查 Docker 环境...

docker --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo %RED%✗ 未检测到 Docker！%RESET%
    echo   请先安装 Docker Desktop: https://www.docker.com/products/docker-desktop/
    echo   安装后请确保启用 WSL2 后端
    exit /b 1
)

docker compose version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo %RED%✗ 未检测到 Docker Compose！%RESET%
    echo   Docker Desktop 通常自带 Docker Compose
    echo   请确保 Docker Desktop 已正确安装
    exit /b 1
)

REM 检查 Docker 是否正在运行
docker info >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo %RED%✗ Docker 未运行！%RESET%
    echo   请先启动 Docker Desktop，等待其完全启动后再运行此脚本
    exit /b 1
)

echo %GREEN%✓ Docker 环境就绪%RESET%

REM ---- Step 2: 检查并创建 .env ----
echo %YELLOW%[2/6]%RESET% 检查环境变量配置...

if not exist ".env" (
    echo   .env 文件不存在，正在从模板创建...
    copy .env.example .env >nul

    REM 生成随机 JWT_SECRET
    for /f "delims=" %%i in ('powershell -Command "[System.Guid]::NewGuid().ToString('N') + [System.Guid]::NewGuid().ToString('N')"') do set "JWT_SECRET=%%i"
    powershell -Command "(Get-Content .env) -replace 'change-me-to-a-secure-random-string', '%JWT_SECRET%' | Set-Content .env"

    echo %GREEN%✓ .env 文件已创建%RESET%
    echo.
    echo %YELLOW%  ⚠  请编辑 .env 文件填入以下关键配置:%RESET%
    echo     - OPENAI_API_KEY    (必需 - AI 摘要/分类功能)
    echo     - TWITTER_BEARER_TOKEN  (可选 - Twitter 数据源)
    echo     - REDDIT_CLIENT_ID/SECRET (可选 - Reddit 数据源)
    echo     - GITHUB_TOKEN      (可选 - GitHub 数据源)
    echo.
    set /p CONTINUE=  现在编辑还是稍后配置？(按 Enter 继续启动 / 输入 e 打开编辑器):
    if /i "!CONTINUE!"=="e" (
        notepad .env
        echo   编辑完成后请重新运行此脚本
        exit /b 0
    )
) else (
    echo %GREEN%✓ .env 文件已存在%RESET%
)

REM ---- Step 3: 构建并启动容器 ----
if defined REBUILD (
    echo %YELLOW%[3/6]%RESET% 重新构建并启动所有服务 (--rebuild)...
    docker compose down >nul 2>&1
    docker compose up -d --build
) else (
    echo %YELLOW%[3/6]%RESET% 启动所有服务...
    docker compose up -d --build
)

if %ERRORLEVEL% NEQ 0 (
    echo %RED%✗ 服务启动失败！%RESET%
    echo   请检查 Docker Desktop 是否正常运行
    echo   可运行 docker compose logs 查看详细日志
    exit /b 1
)

echo %GREEN%✓ 所有容器已启动%RESET%

REM ---- Step 4: 等待数据库就绪 ----
echo %YELLOW%[4/6]%RESET% 等待数据库就绪...

set "RETRIES=0"
set "MAX_RETRIES=30"

:wait_db
set /a RETRIES+=1
if %RETRIES% GTR %MAX_RETRIES% (
    echo %RED%✗ 数据库启动超时！%RESET%
    echo   请运行: docker compose logs postgres
    exit /b 1
)

docker compose exec -T postgres pg_isready -U gamewire >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    <nul set /p="."
    timeout /t 1 /nobreak >nul
    goto :wait_db
)
echo.
echo %GREEN%✓ PostgreSQL 已就绪%RESET%

REM 检查 Redis
docker compose exec -T redis redis-cli ping >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo %YELLOW%  等待 Redis...%RESET%
    timeout /t 3 /nobreak >nul
)
echo %GREEN%✓ Redis 已就绪%RESET%

REM ---- Step 5: 数据库迁移 ----
echo %YELLOW%[5/6]%RESET% 执行数据库迁移...

docker compose exec -T backend alembic upgrade head 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo %YELLOW%  ⚠ 数据库迁移可能已是最新状态%RESET%
) else (
    echo %GREEN%✓ 数据库迁移完成%RESET%
)

REM ---- Step 6: 种子数据 ----
echo %YELLOW%[6/6]%RESET% 初始化种子数据...

docker compose exec -T backend python -m app.seed 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo %YELLOW%  ⚠ 种子数据可能已存在，跳过%RESET%
) else (
    echo %GREEN%✓ 种子数据初始化完成%RESET%
)

REM ---- 完成 ----
echo.
echo %GREEN%%BOLD%=========================================%RESET%
echo %GREEN%%BOLD%  ✅ GameWire 启动成功！%RESET%
echo %GREEN%%BOLD%=========================================%RESET%
echo.
echo   🌐 前端界面:  %BOLD%http://localhost:5173%RESET%
echo   🔌 后端 API:  %BOLD%http://localhost:8000%RESET%
echo   📚 API 文档:  %BOLD%http://localhost:8000/docs%RESET%
echo.
echo   👤 默认管理员: admin@gamewire.local
echo   🔑 默认密码:   (见 .env 中 DEFAULT_ADMIN_PASSWORD)
echo.
echo   常用命令:
echo     查看日志:     docker compose logs -f
echo     停止服务:     scripts\start.bat --stop
echo     重新构建:     scripts\start.bat --rebuild
echo     数据库备份:   scripts\backup.bat
echo.
exit /b 0

:stop_services
echo %YELLOW%正在停止所有 GameWire 服务...%RESET%
docker compose down
echo %GREEN%✓ 所有服务已停止%RESET%
exit /b 0

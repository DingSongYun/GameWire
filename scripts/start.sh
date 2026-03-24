#!/usr/bin/env bash
# ============================================
#  GameWire 一键启动脚本 (Linux / macOS)
#  用法: ./scripts/start.sh [--rebuild] [--stop]
# ============================================

set -euo pipefail

# ---- 颜色定义 ----
BLUE='\033[0;94m'
GREEN='\033[0;92m'
YELLOW='\033[0;93m'
RED='\033[0;91m'
BOLD='\033[1m'
RESET='\033[0m'

# ---- 定位项目根目录 ----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# ---- 辅助函数 ----
info()    { echo -e "${YELLOW}$1${RESET}"; }
success() { echo -e "${GREEN}✓ $1${RESET}"; }
error()   { echo -e "${RED}✗ $1${RESET}"; }
header()  { echo -e "${BLUE}${BOLD}$1${RESET}"; }

# ---- 停止服务 ----
stop_services() {
    info "正在停止所有 GameWire 服务..."
    docker compose down
    success "所有服务已停止"
    exit 0
}

# ---- 参数处理 ----
REBUILD=false
for arg in "$@"; do
    case $arg in
        --stop)    stop_services ;;
        --rebuild) REBUILD=true ;;
        --help|-h)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --rebuild  重新构建所有镜像并启动"
            echo "  --stop     停止所有服务"
            echo "  --help     显示帮助信息"
            exit 0
            ;;
    esac
done

echo ""
header "========================================="
header "  🎮 GameWire - 游戏行业资讯聚合平台"
header "========================================="
echo ""

# ---- Step 1: 检查 Docker ----
info "[1/6] 检查 Docker 环境..."

if ! command -v docker &> /dev/null; then
    error "未检测到 Docker！"
    echo "  请先安装 Docker:"
    echo "  - Ubuntu/Debian: https://docs.docker.com/engine/install/ubuntu/"
    echo "  - macOS: https://docs.docker.com/desktop/install/mac-install/"
    echo "  - CentOS: https://docs.docker.com/engine/install/centos/"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    # 兼容旧版 docker-compose
    if ! command -v docker-compose &> /dev/null; then
        error "未检测到 Docker Compose！"
        echo "  请安装 Docker Compose: https://docs.docker.com/compose/install/"
        exit 1
    fi
    COMPOSE_CMD="docker-compose"
else
    COMPOSE_CMD="docker compose"
fi

if ! docker info &> /dev/null; then
    error "Docker 守护进程未运行！"
    echo "  请启动 Docker:"
    echo "  - Linux: sudo systemctl start docker"
    echo "  - macOS: 启动 Docker Desktop 应用"
    exit 1
fi

success "Docker 环境就绪 ($(docker --version | head -1))"

# ---- Step 2: 检查并创建 .env ----
info "[2/6] 检查环境变量配置..."

if [ ! -f ".env" ]; then
    echo "  .env 文件不存在，正在从模板创建..."
    cp .env.example .env

    # 生成随机 JWT_SECRET
    if command -v openssl &> /dev/null; then
        JWT_SECRET=$(openssl rand -hex 32)
    elif command -v python3 &> /dev/null; then
        JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    else
        JWT_SECRET=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 64 | head -n 1)
    fi

    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS sed 语法
        sed -i '' "s/change-me-to-a-secure-random-string/${JWT_SECRET}/" .env
    else
        sed -i "s/change-me-to-a-secure-random-string/${JWT_SECRET}/" .env
    fi

    success ".env 文件已创建 (JWT_SECRET 已自动生成)"
    echo ""
    echo -e "  ${YELLOW}⚠  请编辑 .env 文件填入以下关键配置:${RESET}"
    echo "     - OPENAI_API_KEY         (必需 - AI 摘要/分类功能)"
    echo "     - TWITTER_BEARER_TOKEN   (可选 - Twitter 数据源)"
    echo "     - REDDIT_CLIENT_ID/SECRET(可选 - Reddit 数据源)"
    echo "     - GITHUB_TOKEN           (可选 - GitHub 数据源)"
    echo ""
    read -p "  现在编辑还是稍后配置？(按 Enter 继续启动 / 输入 e 打开编辑器): " EDIT_CHOICE
    if [[ "$EDIT_CHOICE" == "e" || "$EDIT_CHOICE" == "E" ]]; then
        ${EDITOR:-nano} .env
        echo "  编辑完成，继续启动..."
    fi
else
    success ".env 文件已存在"
fi

# ---- Step 3: 构建并启动容器 ----
if [ "$REBUILD" = true ]; then
    info "[3/6] 重新构建并启动所有服务 (--rebuild)..."
    $COMPOSE_CMD down 2>/dev/null || true
    $COMPOSE_CMD up -d --build
else
    info "[3/6] 启动所有服务..."
    $COMPOSE_CMD up -d --build
fi

success "所有容器已启动"

# ---- Step 4: 等待数据库就绪 ----
info "[4/6] 等待数据库就绪..."

RETRIES=0
MAX_RETRIES=30

while ! $COMPOSE_CMD exec -T postgres pg_isready -U gamewire &> /dev/null; do
    RETRIES=$((RETRIES + 1))
    if [ $RETRIES -gt $MAX_RETRIES ]; then
        error "数据库启动超时！"
        echo "  请运行: $COMPOSE_CMD logs postgres"
        exit 1
    fi
    printf "."
    sleep 1
done
echo ""
success "PostgreSQL 已就绪"

# 等待 Redis
RETRIES=0
while ! $COMPOSE_CMD exec -T redis redis-cli ping &> /dev/null; do
    RETRIES=$((RETRIES + 1))
    if [ $RETRIES -gt 10 ]; then
        error "Redis 启动超时！"
        exit 1
    fi
    sleep 1
done
success "Redis 已就绪"

# 等待 Backend 启动
info "  等待后端服务启动..."
RETRIES=0
while ! $COMPOSE_CMD exec -T backend python -c "print('ok')" &> /dev/null; do
    RETRIES=$((RETRIES + 1))
    if [ $RETRIES -gt 30 ]; then
        error "后端服务启动超时！"
        echo "  请运行: $COMPOSE_CMD logs backend"
        exit 1
    fi
    printf "."
    sleep 2
done
echo ""
success "后端服务已就绪"

# ---- Step 5: 数据库迁移 ----
info "[5/6] 执行数据库迁移..."

if $COMPOSE_CMD exec -T backend alembic upgrade head 2>&1; then
    success "数据库迁移完成"
else
    echo -e "  ${YELLOW}⚠ 数据库迁移可能已是最新状态${RESET}"
fi

# ---- Step 6: 种子数据 ----
info "[6/6] 初始化种子数据..."

if $COMPOSE_CMD exec -T backend python -m app.seed 2>&1; then
    success "种子数据初始化完成"
else
    echo -e "  ${YELLOW}⚠ 种子数据可能已存在，跳过${RESET}"
fi

# ---- 完成 ----
echo ""
echo -e "${GREEN}${BOLD}=========================================${RESET}"
echo -e "${GREEN}${BOLD}  ✅ GameWire 启动成功！${RESET}"
echo -e "${GREEN}${BOLD}=========================================${RESET}"
echo ""
echo -e "  🌐 前端界面:  ${BOLD}http://localhost:5173${RESET}"
echo -e "  🔌 后端 API:  ${BOLD}http://localhost:8000${RESET}"
echo -e "  📚 API 文档:  ${BOLD}http://localhost:8000/docs${RESET}"
echo ""
echo "  👤 默认管理员: admin@gamewire.local"
echo "  🔑 默认密码:   (见 .env 中 DEFAULT_ADMIN_PASSWORD)"
echo ""
echo "  常用命令:"
echo "    查看日志:     $COMPOSE_CMD logs -f"
echo "    停止服务:     ./scripts/start.sh --stop"
echo "    重新构建:     ./scripts/start.sh --rebuild"
echo "    数据库备份:   ./scripts/backup.sh"
echo ""

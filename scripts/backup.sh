#!/usr/bin/env bash
# ============================================
#  GameWire 数据库备份脚本 (Linux / macOS)
#  用法: ./scripts/backup.sh [备份目录]
# ============================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

BACKUP_DIR="${1:-./backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/gamewire_${TIMESTAMP}.sql"

mkdir -p "$BACKUP_DIR"

echo "[GameWire] 正在备份数据库..."

if docker compose exec -T postgres pg_dump -U gamewire gamewire > "$BACKUP_FILE"; then
    echo "[GameWire] 备份成功: $BACKUP_FILE"
else
    echo "[GameWire] 备份失败!"
    exit 1
fi

# 清理 7 天前的备份
find "$BACKUP_DIR" -name "gamewire_*.sql" -mtime +7 -delete 2>/dev/null || true
echo "[GameWire] 已清理 7 天前的旧备份"

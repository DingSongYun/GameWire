#!/usr/bin/env bash
# ============================================
#  GameWire 数据库恢复脚本 (Linux / macOS)
#  用法: ./scripts/restore.sh <备份文件路径>
# ============================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

BACKUP_FILE="${1:-}"

if [ -z "$BACKUP_FILE" ]; then
    echo "用法: ./scripts/restore.sh <备份文件路径>"
    echo "示例: ./scripts/restore.sh backups/gamewire_20240115_100000.sql"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "[GameWire] 错误: 备份文件不存在: $BACKUP_FILE"
    exit 1
fi

echo "[GameWire] 警告: 这将覆盖现有数据库!"
read -p "确认恢复? (y/N): " CONFIRM
if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
    echo "[GameWire] 已取消"
    exit 0
fi

echo "[GameWire] 正在恢复数据库..."

if docker compose exec -T postgres psql -U gamewire -d gamewire < "$BACKUP_FILE"; then
    echo "[GameWire] 恢复成功!"
else
    echo "[GameWire] 恢复失败!"
    exit 1
fi

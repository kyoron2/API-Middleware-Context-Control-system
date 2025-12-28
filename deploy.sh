#!/bin/bash

# API Middleware 自动部署脚本
# 用途：从 Gitee 拉取最新代码并重启 Docker 服务

set -e  # 遇到错误立即退出

# ========== 配置区域 ==========
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"  # 自动获取脚本所在目录
BRANCH="main"  # 要部署的分支，根据你的实际分支修改（main 或 master）
LOG_FILE="$PROJECT_DIR/deploy.log"  # 日志文件路径
# ==============================

# 日志函数
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

cd "$PROJECT_DIR"

log "========== 开始自动部署 =========="

# 1. 拉取最新代码
log "拉取最新代码..."
BEFORE_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
git fetch origin
git reset --hard origin/$BRANCH  # 强制更新到远程最新版本

AFTER_COMMIT=$(git rev-parse HEAD)

# 2. 检查是否有更新
if [ "$BEFORE_COMMIT" = "$AFTER_COMMIT" ]; then
    log "代码已是最新，无需重新部署"
    exit 0
fi

log "检测到代码更新: $BEFORE_COMMIT -> $AFTER_COMMIT"

# 3. 检查是否需要重建镜像
REBUILD_NEEDED=false
CHANGED_FILES=$(git diff --name-only "$BEFORE_COMMIT" "$AFTER_COMMIT" 2>/dev/null || echo "")

if echo "$CHANGED_FILES" | grep -qE "(Dockerfile|pyproject.toml|requirements.txt|uv.lock)"; then
    REBUILD_NEEDED=true
fi

# 4. 重启服务
if [ "$REBUILD_NEEDED" = true ]; then
    log "检测到依赖变化，重建镜像并重启..."
    docker-compose down
    docker-compose build --no-cache
    docker-compose up -d
else
    log "仅代码变化，快速重启..."
    docker-compose restart middleware
fi

# 5. 等待服务启动
log "等待服务启动..."
sleep 5

# 6. 健康检查
log "执行健康检查..."
for i in {1..10}; do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log "✓ 服务启动成功"
        log "当前版本: $(git rev-parse --short HEAD)"
        log "========== 部署完成 =========="
        
        # 清理旧镜像
        docker image prune -f > /dev/null 2>&1
        
        exit 0
    fi
    log "等待服务启动... ($i/10)"
    sleep 3
done

log "✗ 服务启动失败，请检查日志"
docker-compose logs --tail=50 middleware
exit 1

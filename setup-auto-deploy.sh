#!/bin/bash

# 自动部署设置脚本 - 简化版（适用于 Gitee + Docker）

set -e

echo "========================================"
echo "  API Middleware 自动部署配置"
echo "========================================"
echo ""

# 获取当前项目路径
CURRENT_DIR=$(pwd)
echo "当前项目路径: $CURRENT_DIR"
echo ""

# 给脚本添加执行权限
chmod +x deploy.sh

echo "配置定时拉取（每 5 分钟检查一次更新）..."
echo ""

# 检查是否已存在定时任务
if crontab -l 2>/dev/null | grep -q "deploy.sh"; then
    echo "⚠️  定时任务已存在"
    echo ""
    read -p "是否要重新配置？(y/n): " CONFIRM
    if [ "$CONFIRM" != "y" ]; then
        echo "取消配置"
        exit 0
    fi
    # 删除旧的定时任务
    crontab -l 2>/dev/null | grep -v "deploy.sh" | crontab -
fi

# 添加定时任务（每 5 分钟执行一次）
(crontab -l 2>/dev/null; echo "*/5 * * * * cd $CURRENT_DIR && ./deploy.sh >> $CURRENT_DIR/deploy.log 2>&1") | crontab -

echo "✓ 定时任务已添加"
echo ""
echo "=========================================="
echo "配置完成！"
echo "=========================================="
echo ""
echo "部署脚本: $CURRENT_DIR/deploy.sh"
echo "日志文件: $CURRENT_DIR/deploy.log"
echo ""
echo "使用方法:"
echo "  手动部署: ./deploy.sh"
echo "  查看日志: tail -f deploy.log"
echo "  查看定时任务: crontab -l"
echo ""
echo "现在每 5 分钟会自动检查 Gitee 更新并部署"
echo ""

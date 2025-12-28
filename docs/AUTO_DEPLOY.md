# 自动部署配置指南

本文档介绍如何为 API Middleware 配置自动部署，让你的服务器在代码更新后自动拉取并重启。

## 📋 目录

- [方案对比](#方案对比)
- [方案 1: 定时拉取（推荐）](#方案-1-定时拉取推荐)
- [方案 2: Git Webhook](#方案-2-git-webhook)
- [方案 3: GitHub Actions](#方案-3-github-actions)
- [故障排查](#故障排查)

---

## 方案对比

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| **定时拉取** | 简单、稳定、无需外网访问 | 有延迟（最多 5 分钟） | 内网服务器、个人项目 |
| **Git Webhook** | 实时部署、无延迟 | 需要外网访问、配置复杂 | 公网服务器、团队项目 |
| **GitHub Actions** | 集成 CI/CD、功能强大 | 需要 GitHub、配置 SSH | 使用 GitHub 的项目 |

---

## 方案 1: 定时拉取（推荐）

### 特点
- ✅ 最简单、最稳定
- ✅ 无需外网访问
- ✅ 自动检测更新并部署
- ⏱️ 延迟：最多 5 分钟

### 快速开始

#### 1. 运行配置脚本

```bash
chmod +x setup-auto-deploy.sh
./setup-auto-deploy.sh
```

选择选项 `1` (定时拉取)

#### 2. 验证配置

```bash
# 查看定时任务
crontab -l

# 手动测试部署
./deploy.sh

# 查看部署日志
tail -f /var/log/api-middleware-deploy.log
```

#### 3. 完成！

现在每 5 分钟会自动检查代码更新，如果有更新会自动部署。

### 自定义配置

#### 修改检查频率

编辑 crontab：

```bash
crontab -e
```

修改定时规则：

```bash
# 每 5 分钟检查一次（默认）
*/5 * * * * /path/to/project/deploy.sh

# 每 10 分钟检查一次
*/10 * * * * /path/to/project/deploy.sh

# 每小时检查一次
0 * * * * /path/to/project/deploy.sh

# 每天凌晨 2 点检查一次
0 2 * * * /path/to/project/deploy.sh
```

#### 修改部署分支

编辑 `deploy.sh`：

```bash
BRANCH="main"  # 修改为你的分支名
```

---

## 方案 2: Git Webhook

### 特点
- ✅ 实时部署（推送后立即部署）
- ✅ 无延迟
- ❌ 需要服务器能被外网访问
- ❌ 配置相对复杂

### 快速开始

#### 1. 运行配置脚本

```bash
chmod +x setup-auto-deploy.sh
./setup-auto-deploy.sh
```

选择选项 `2` (Git Webhook)

#### 2. 修改 Webhook 密钥

编辑 `webhook-server.py`：

```python
SECRET = 'your-strong-secret-key-here'  # 修改为强密码
```

#### 3. 安装 systemd 服务

```bash
sudo cp /tmp/webhook-deploy.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable webhook-deploy
sudo systemctl start webhook-deploy
```

#### 4. 开放防火墙端口

```bash
# Ubuntu/Debian
sudo ufw allow 9000

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=9000/tcp
sudo firewall-cmd --reload
```

#### 5. 配置 GitHub Webhook

1. 进入你的 GitHub 仓库
2. 点击 `Settings` → `Webhooks` → `Add webhook`
3. 填写配置：
   - **Payload URL**: `http://your-server-ip:9000/deploy`
   - **Content type**: `application/json`
   - **Secret**: 你在步骤 2 中设置的密钥
   - **Events**: 选择 `Just the push event`
4. 点击 `Add webhook`

#### 6. 测试

推送代码到 main 分支，查看日志：

```bash
sudo journalctl -u webhook-deploy -f
```

---

## 方案 3: GitHub Actions

### 特点
- ✅ 集成 CI/CD 流程
- ✅ 可以添加测试、构建等步骤
- ✅ 支持多环境部署
- ❌ 需要配置 SSH 密钥
- ❌ 仅支持 GitHub

### 快速开始

#### 1. 生成 SSH 密钥对

在你的**本地机器**上：

```bash
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/github_actions
```

#### 2. 添加公钥到服务器

```bash
# 复制公钥到服务器
ssh-copy-id -i ~/.ssh/github_actions.pub user@your-server

# 或手动添加
cat ~/.ssh/github_actions.pub
# 将输出的内容添加到服务器的 ~/.ssh/authorized_keys
```

#### 3. 配置 GitHub Secrets

1. 进入你的 GitHub 仓库
2. 点击 `Settings` → `Secrets and variables` → `Actions`
3. 添加以下 secrets：

| Name | Value | 说明 |
|------|-------|------|
| `SERVER_HOST` | `your-server-ip` | 服务器 IP 地址 |
| `SERVER_USER` | `your-username` | SSH 用户名 |
| `SERVER_SSH_KEY` | `私钥内容` | 步骤 1 生成的私钥（~/.ssh/github_actions） |
| `SERVER_PORT` | `22` | SSH 端口（可选，默认 22） |

#### 4. 修改工作流文件

编辑 `.github/workflows/auto-deploy.yml`：

```yaml
script: |
  cd /path/to/your/project  # 修改为你的实际项目路径
  ./deploy.sh
```

#### 5. 测试

推送代码到 main 分支，查看 GitHub Actions 运行结果：

1. 进入仓库的 `Actions` 标签
2. 查看最新的工作流运行
3. 点击查看详细日志

---

## 高级配置

### 1. 添加部署通知

#### Slack 通知

在 `deploy.sh` 末尾添加：

```bash
# Slack Webhook URL
SLACK_WEBHOOK="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

# 发送通知
curl -X POST "$SLACK_WEBHOOK" \
  -H 'Content-Type: application/json' \
  -d "{
    \"text\": \"✓ API Middleware 部署成功\",
    \"attachments\": [{
      \"color\": \"good\",
      \"fields\": [
        {\"title\": \"版本\", \"value\": \"$(git rev-parse --short HEAD)\", \"short\": true},
        {\"title\": \"时间\", \"value\": \"$(date)\", \"short\": true}
      ]
    }]
  }"
```

#### 邮件通知

```bash
# 发送邮件
echo "部署完成: $(git rev-parse --short HEAD)" | \
  mail -s "API Middleware 部署通知" your-email@example.com
```

### 2. 回滚功能

如果部署失败，脚本会自动回滚到之前的版本。你也可以手动回滚：

```bash
# 查看最近的提交
git log --oneline -10

# 回滚到指定版本
git checkout <commit-hash>
docker-compose restart middleware
```

### 3. 蓝绿部署

如果需要零停机部署，可以配置蓝绿部署：

```bash
# 启动新版本（使用不同端口）
docker-compose -f docker-compose.blue.yml up -d

# 健康检查通过后，切换流量
# 更新 Nginx 配置指向新端口

# 停止旧版本
docker-compose -f docker-compose.green.yml down
```

---

## 故障排查

### 问题 1: 定时任务不执行

**检查 crontab 是否正确配置：**

```bash
crontab -l
```

**检查 cron 服务是否运行：**

```bash
sudo systemctl status cron
```

**查看 cron 日志：**

```bash
grep CRON /var/log/syslog
```

### 问题 2: 部署脚本执行失败

**查看部署日志：**

```bash
tail -f /var/log/api-middleware-deploy.log
```

**手动执行脚本查看错误：**

```bash
cd /path/to/project
./deploy.sh
```

**常见错误：**

- **权限问题**: `chmod +x deploy.sh`
- **Git 权限**: 确保有 SSH 密钥或 HTTPS 凭据
- **Docker 权限**: 将用户添加到 docker 组

### 问题 3: Webhook 服务无法访问

**检查服务状态：**

```bash
sudo systemctl status webhook-deploy
```

**查看服务日志：**

```bash
sudo journalctl -u webhook-deploy -f
```

**检查端口是否开放：**

```bash
sudo netstat -tlnp | grep 9000
```

**测试 Webhook：**

```bash
curl -X POST http://localhost:9000/deploy \
  -H "Content-Type: application/json" \
  -d '{"ref":"refs/heads/main"}'
```

### 问题 4: GitHub Actions 部署失败

**检查 Secrets 配置：**

确保所有必需的 secrets 都已正确配置。

**检查 SSH 连接：**

```bash
ssh -i ~/.ssh/github_actions user@your-server
```

**查看 Actions 日志：**

在 GitHub 仓库的 Actions 标签中查看详细错误信息。

---

## 安全建议

### 1. 使用 SSH 密钥

不要在脚本中硬编码密码，使用 SSH 密钥认证：

```bash
# 生成密钥
ssh-keygen -t ed25519

# 添加到服务器
ssh-copy-id user@server
```

### 2. 限制 Webhook 访问

使用防火墙限制 Webhook 端口只能从 GitHub IP 访问：

```bash
# 允许 GitHub Webhook IP 段
sudo ufw allow from 140.82.112.0/20 to any port 9000
```

### 3. 使用强密钥

Webhook 密钥应该使用强随机字符串：

```bash
# 生成强密钥
openssl rand -hex 32
```

### 4. 定期审查日志

定期检查部署日志，发现异常活动：

```bash
tail -100 /var/log/api-middleware-deploy.log
```

---

## 监控和维护

### 1. 设置日志轮转

创建 `/etc/logrotate.d/api-middleware-deploy`：

```
/var/log/api-middleware-deploy.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

### 2. 监控部署状态

使用监控工具（如 Prometheus + Grafana）监控：

- 部署频率
- 部署成功率
- 部署耗时
- 服务健康状态

### 3. 定期备份

在部署前自动备份：

```bash
# 在 deploy.sh 中添加
BACKUP_DIR="/backup/api-middleware"
mkdir -p "$BACKUP_DIR"
tar -czf "$BACKUP_DIR/backup-$(date +%Y%m%d-%H%M%S).tar.gz" \
  config/ .env
```

---

## 总结

推荐配置方案：

- **个人项目/内网**: 使用方案 1（定时拉取）
- **团队项目/公网**: 使用方案 2（Webhook）或方案 3（GitHub Actions）
- **生产环境**: 结合使用，添加监控和告警

选择适合你的方案，开始自动化部署吧！🚀

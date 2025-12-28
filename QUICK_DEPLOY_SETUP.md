# 🚀 快速配置自动部署

只需 3 步，让你的服务器自动拉取代码并重启！

## 📦 方案选择

### 方案 1: 定时拉取（最简单，推荐）⭐

**适合**: 个人项目、内网服务器

```bash
# 1. 给脚本添加执行权限
chmod +x setup-auto-deploy.sh deploy.sh

# 2. 运行配置向导
./setup-auto-deploy.sh

# 3. 选择选项 1，完成！
```

✅ 配置完成后，每 5 分钟自动检查更新并部署

---

### 方案 2: Git Webhook（实时部署）

**适合**: 公网服务器、团队项目

```bash
# 1. 给脚本添加执行权限
chmod +x setup-auto-deploy.sh deploy.sh

# 2. 运行配置向导
./setup-auto-deploy.sh

# 3. 选择选项 2

# 4. 修改密钥
nano webhook-server.py  # 修改 SECRET 变量

# 5. 安装服务
sudo cp /tmp/webhook-deploy.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable webhook-deploy
sudo systemctl start webhook-deploy

# 6. 开放端口
sudo ufw allow 9000

# 7. 在 GitHub 配置 Webhook
# URL: http://your-server-ip:9000/deploy
# Secret: 你设置的密钥
```

---

### 方案 3: GitHub Actions（CI/CD）

**适合**: 使用 GitHub 的项目

```bash
# 1. 生成 SSH 密钥
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/github_actions

# 2. 添加公钥到服务器
ssh-copy-id -i ~/.ssh/github_actions.pub user@your-server

# 3. 在 GitHub 仓库配置 Secrets:
# - SERVER_HOST: 服务器 IP
# - SERVER_USER: SSH 用户名
# - SERVER_SSH_KEY: 私钥内容（cat ~/.ssh/github_actions）

# 4. 修改 .github/workflows/auto-deploy.yml 中的项目路径

# 5. 推送代码，自动部署！
```

---

## 🔍 验证部署

### 查看部署日志

```bash
# 方案 1 (定时拉取)
tail -f /var/log/api-middleware-deploy.log

# 方案 2 (Webhook)
sudo journalctl -u webhook-deploy -f

# 方案 3 (GitHub Actions)
# 在 GitHub 仓库的 Actions 标签查看
```

### 手动触发部署

```bash
# 直接运行部署脚本
./deploy.sh

# 或使用快捷命令（方案 1 配置后）
source ~/.bashrc
deploy-api
```

### 检查服务状态

```bash
# 查看容器状态
docker-compose ps

# 健康检查
curl http://localhost:8000/health

# 查看日志
docker-compose logs -f middleware
```

---

## ⚙️ 常用命令

```bash
# 查看定时任务
crontab -l

# 编辑定时任务
crontab -e

# 查看 Webhook 服务状态
sudo systemctl status webhook-deploy

# 重启 Webhook 服务
sudo systemctl restart webhook-deploy

# 查看最近的 Git 提交
git log --oneline -10

# 手动回滚到指定版本
git checkout <commit-hash>
docker-compose restart middleware
```

---

## 📚 详细文档

查看完整文档: [docs/AUTO_DEPLOY.md](docs/AUTO_DEPLOY.md)

---

## 🆘 遇到问题？

### 定时任务不执行

```bash
# 检查 cron 服务
sudo systemctl status cron

# 查看 cron 日志
grep CRON /var/log/syslog
```

### 部署脚本失败

```bash
# 查看详细错误
./deploy.sh

# 检查权限
chmod +x deploy.sh
```

### Webhook 无法访问

```bash
# 检查端口
sudo netstat -tlnp | grep 9000

# 检查防火墙
sudo ufw status
```

---

## 💡 提示

- **首次配置**: 建议先手动运行 `./deploy.sh` 测试
- **修改频率**: 编辑 crontab 调整检查间隔
- **查看日志**: 定期检查部署日志确保正常运行
- **安全性**: 使用 SSH 密钥而不是密码

---

**配置完成后，你只需要 `git push`，服务器会自动更新！** 🎉

# 《基础工程》智慧学伴

面向湖南大学土木工程学院《基础工程》课程的三角色智慧教学平台。

## 平台能力

- 学生端：教材、知识图谱、服务端 RAG 问答、关联规范、全书题库、学习进度与报告。
- 教师端：班级和学生、资料上传与 RAG 切块、题库、作业、批改、学情和通知。
- 管理员端：教师、学生、班级、强绑定、导入预检、账号安全和操作日志。
- 安全：服务端图片验证码、Argon2 密码、HttpOnly 会话、CSRF、角色 API 权限和登录限流。

## 本地开发

```bash
npm install
python3 -m venv server/.venv
server/.venv/bin/pip install -r server/requirements.txt
FOUNDATION_SECRET_KEY=local-dev-secret server/.venv/bin/python -m server.manage migrate
FOUNDATION_SECRET_KEY=local-dev-secret server/.venv/bin/uvicorn server.app:app --host 127.0.0.1 --port 8000
npm run dev
```

前端开发服务会把 `/api` 代理到 `http://127.0.0.1:8000`。

## 数据库

生产环境使用 PostgreSQL，测试使用 SQLite。配置参考 `server/.env.example`。

```bash
server/.venv/bin/python -m server.manage migrate
server/.venv/bin/python -m server.manage import-legacy /path/to/app.db
```

旧 SQLite 数据导入是幂等事务，原数据库会保留用于回滚。教材切块存放在 `server/data/knowledge/`，不会复制到公开静态目录。

## RAG 与大模型

未配置大模型时，问答仍会返回服务端 RAG 检索答案和引用。配置 OpenAI-compatible Chat Completions 接口后会生成基于召回片段的答案：

```bash
FOUNDATION_LLM_API_URL=https://example.com/v1/chat/completions
FOUNDATION_LLM_API_KEY=your-api-key
FOUNDATION_LLM_MODEL=your-model
```

## 验证与部署

```bash
npm run check
bash scripts/deploy-platform-jdcloud.sh
```

部署脚本执行测试、构建、数据库迁移、旧数据幂等导入、后端和前端原子切换、服务重启与线上健康检查。生产入口保持：

`http://111.228.5.243/foundation-smart-companion/`

### 生产环境变量

服务器从 `/etc/foundation-smart-companion.env` 读取配置，文件权限应设为 `600`。至少需要：

```bash
FOUNDATION_DATABASE_URL=postgresql+psycopg://foundation_app:password@127.0.0.1/foundation_smart_companion
FOUNDATION_SECRET_KEY=replace-with-a-long-random-secret
FOUNDATION_UPLOAD_DIR=/var/lib/foundation-smart-companion/uploads
FOUNDATION_ALLOWED_ORIGINS=http://111.228.5.243
```

大模型变量见上方“RAG 与大模型”。未配置时保留服务端检索与引用，不会阻断教材问答。

### HTTPS 升级

为服务器绑定域名并完成 DNS 解析后，可用 Certbot 为现有 Nginx 站点签发证书：

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.example
```

签发后把 `FOUNDATION_ALLOWED_ORIGINS` 改为 HTTPS 域名，重启 API，并验证登录、验证码和上传接口。IP 地址入口暂时保留 HTTP，不应直接签发公开 TLS 证书。

### 回滚

发布目录默认保留最近 5 个版本。选择上一版前后端目录并原子切换软链接：

```bash
sudo ln -sfn /opt/foundation-smart-companion-releases/releases/<release> /opt/foundation-smart-companion.next
sudo mv -Tf /opt/foundation-smart-companion.next /opt/foundation-smart-companion
sudo ln -sfn /var/www/releases/foundation-smart-companion/releases/<release> /var/www/foundation-smart-companion.next
sudo mv -Tf /var/www/foundation-smart-companion.next /var/www/foundation-smart-companion
sudo systemctl restart foundation-smart-companion-api
sudo nginx -t && sudo systemctl reload nginx
```

数据库迁移前的完整备份位于 `/var/backups/foundation-smart-companion/`；仅在代码回滚仍无法恢复兼容性时，再按备份说明恢复数据库。

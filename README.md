# 《基础工程》智慧学伴

面向土木工程《基础工程》课程的智慧学习平台。

## 功能模块

- 课程总览
- 教材学习
- 知识图谱
- 智能问答
- 工程案例
- 关联资料
- 练习中心
- 学习报告
- 后台管理

## 本地运行

```bash
npm install
npm run dev
```

如需运行真实多人后端：

```bash
python3 -m venv server/.venv
server/.venv/bin/pip install -r server/requirements.txt
FOUNDATION_SECRET_KEY=local-dev-secret server/.venv/bin/uvicorn server.app:app --host 127.0.0.1 --port 8000
```

前端开发服务已把 `/api` 代理到 `http://127.0.0.1:8000`。

## 构建

```bash
npm run build
```

## 说明

当前包含两层能力：

- 前端：课程展示、知识图谱、练习、登录界面和后台界面。
- 后端：FastAPI + SQLite，提供真实登录、教师知识库上传、题库导入、答疑配置和服务端 RAG 问答。

课程章节口径统一来自 `public/course-manifest.json`。首页进度、教材章节入口、章节快捷入口、学习报告和题库章节匹配都应以这份 manifest 为准，避免页面之间出现不同章节总数。

默认账号：

- 学生：`student / 123456`
- 指导老师：`teacher / 123456`
- 管理员：`admin / 123456`

生产环境建议启动后立即修改默认密码，并设置 `FOUNDATION_SECRET_KEY`。大模型接口使用 OpenAI-compatible 配置：

```bash
FOUNDATION_LLM_API_URL=https://example.com/v1/chat/completions
FOUNDATION_LLM_API_KEY=your-api-key
FOUNDATION_LLM_MODEL=your-model
```

未配置大模型时，`/api/qa` 仍会返回服务端 RAG 检索答案和引用来源。

前端同时接入 Puter.js 免费浏览器端 AI：点击“AI生成”时，系统会先从服务器检索教材和教师上传资料，再把 RAG 片段交给浏览器端免费 AI 生成回答；首次使用可能需要在弹出的 Puter 授权窗口中确认。如果第三方免费 AI 不可用，则保留服务器 RAG 答案。学校正式长期使用时，建议在服务器配置稳定的 OpenAI-compatible 模型 API Key。

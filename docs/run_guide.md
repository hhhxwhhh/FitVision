# 本地运行指南

本指南介绍如何从零运行 FitVision。推荐使用 **Docker Compose** 一键启动；
需要调试 AI / 推荐代码时使用本地开发模式。

---

## 1. 环境要求

| 工具 | 版本 | 用途 |
| --- | --- | --- |
| Python | 3.12（≥ 3.10） | 后端 |
| Node.js | ≥ 20.19（推荐 22 LTS） | 前端 |
| Git | 任意较新版本 | 版本控制 |
| Docker + Compose | 可选 | 一键部署 |
| PostgreSQL 16 | 可选 | 默认使用 SQLite |
| Redis 7 | 可选 | 默认使用 LocMem 缓存 |

> 未安装 PostgreSQL / Redis 时项目依然可以完整启动：
> 后端会自动回退到 SQLite 与进程内缓存。

---

## 2. 方式一：Docker Compose（推荐）

```bash
cp .env.docker.example .env
# 至少修改 SECRET_KEY 与 DB_PASSWORD
docker compose up --build
```

启动后：

- 前端：http://localhost:8080
- 后端 API：http://localhost:8000/api/
- Swagger：http://localhost:8000/api/docs/
- 健康检查：http://localhost:8000/api/health/

常用命令：

```bash
docker compose logs -f backend     # 查看后端日志
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py seed_demo   # 已有数据时自动跳过
docker compose down                # 停止
docker compose down -v             # 停止并删除数据卷
```

---

## 3. 方式二：本地开发

### 3.1 后端

```bash
cd backend

python -m venv .venv
# Windows (PowerShell): .venv\Scripts\Activate.ps1
# Windows (Git Bash):   source .venv/Scripts/activate
# macOS / Linux:        source .venv/bin/activate

pip install -r requirements-dev.txt
```

配置环境变量（**可跳过**，默认 SQLite + LocMem）：

```bash
cp .env.example .env
```

`backend/.env` 中与本地开发最相关的几项：

```ini
DEBUG=True
SECRET_KEY=dev-only-change-me

# 不填 DB_* 则使用 SQLite
# DB_NAME=fitvision
# DB_USER=postgres
# DB_PASSWORD=postgres
# DB_HOST=127.0.0.1
# DB_PORT=5432

# 默认 locmem；需要 Redis 时改为 redis
CACHE_BACKEND=locmem
REDIS_URL=redis://127.0.0.1:6379/0

# AI 能力（可选）
CN_VLM_API_KEY=
CN_VLM_MODEL=doubao-1.5-vision-pro-250328
CN_VLM_BASE_URL=https://openkey.cloud/v1
DEEPSEEK_API_KEY=
```

初始化数据库并导入示例数据：

```bash
python manage.py migrate
python manage.py seed_demo                               # 自动导入动作库与示例计划
python manage.py createsuperuser                         # 按需
python manage.py runserver
```

后端运行在 http://127.0.0.1:8000 。

### 3.2 前端

另开一个终端：

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

前端运行在 http://localhost:5173 ，`/api`、`/media`、`/static`
会由 Vite 代理到 `VITE_DEV_PROXY_TARGET`（默认 `http://127.0.0.1:8000`）。

---

## 4. 联调验证

1. 打开前端，注册并登录，确认拿到 access / refresh token。
2. 进入动作库，确认列表与详情可加载。
3. 进入训练页，允许摄像头权限，确认姿态关键点与计数正常。
4. 完成一次训练，查看训练报告与推荐结果。
5. AI 诊断需要有效的 `CN_VLM_API_KEY`，未配置时会提示服务不可用。

---

## 5. 运行测试与检查

```bash
# 后端（不依赖 PostgreSQL / Redis）
cd backend
DB_ENGINE=sqlite CACHE_BACKEND=locmem python manage.py check
DB_ENGINE=sqlite CACHE_BACKEND=locmem python manage.py test

# 前端
cd frontend
npm run lint
npm run type-check
npm run build
```

---

## 6. 常见问题

**摄像头无法打开**
检查浏览器站点权限，关闭占用摄像头的其他应用；`localhost` 与 HTTPS 才允许调用摄像头。

**AI 分析失败**
确认 `CN_VLM_API_KEY` 有效、`CN_VLM_BASE_URL` 可访问；查看后端日志中的上游状态码。
未配置密钥时，注册、训练记录、推荐等核心功能不受影响。

**CORS 错误**
在 `backend/.env` 中把前端地址加入 `CORS_ALLOWED_ORIGINS`，例如
`http://localhost:5173,http://localhost:8080`。

**Redis 连接失败 / Authentication required**
本地未配置 Redis 密码时，保持 `CACHE_BACKEND=locmem`；或把正确的密码写入 `REDIS_URL`。

**向量模型下载慢**
设置 `HF_ENDPOINT=https://hf-mirror.com`（默认值），或提前在本地缓存模型。
首次使用推荐 / 语义检索时会下载 M3E 模型。

**端口冲突**
后端：`python manage.py runserver 8001`；前端：`npm run dev -- --port 5174`，
同时更新 `VITE_DEV_PROXY_TARGET` 并重新启动 Vite。

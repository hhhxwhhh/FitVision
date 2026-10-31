# 部署指南

FitVision 支持 Docker Compose 一键部署，也可拆分前后端独立部署。

## 方式一：Docker Compose（推荐）

```bash
cp .env.docker.example .env
# 编辑 .env：至少设置 SECRET_KEY 与 DB_PASSWORD
docker compose up --build -d
```

| 服务 | 地址 |
| --- | --- |
| 前端 | http://localhost:8080 |
| API 根 | http://localhost:8000/api/ |
| Swagger | http://localhost:8000/api/docs/ |
| 健康检查 | http://localhost:8000/api/health/ |

> 首次构建需下载 PyTorch（CPU 版）与向量模型，耗时较长；后续复用缓存。

## 方式二：前后端独立部署

- **前端**：`npm run build` 产出 `frontend/dist` 静态文件，交给 Nginx / CDN 托管，
  并通过反向代理把 `/api`、`/media` 转发到后端。
- **后端**：使用 `gunicorn fitvision.wsgi:application` 运行，前置 Nginx 处理
  TLS、静态与媒体文件。

## 环境变量（后端 `backend/.env`）

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DEBUG` | `True` | **生产必须为 `False`** |
| `SECRET_KEY` | 开发临时值 | **生产必填**，建议 50+ 位随机串 |
| `ALLOWED_HOSTS` | `127.0.0.1,localhost` | 逗号分隔的域名 |
| `CORS_ALLOWED_ORIGINS` | 本地 5173 / 8080 | 前端源，逗号分隔 |
| `DB_NAME` | 空 | 留空用 SQLite；填写则连 PostgreSQL |
| `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | — | PostgreSQL 连接信息 |
| `CACHE_BACKEND` | `locmem` | `locmem` 或 `redis` |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | 缓存 / Celery |
| `DEEPSEEK_API_KEY` | 空 | 文本生成 / 计划 |
| `CN_VLM_API_KEY` | 空 | 视觉模型 |
| `SENTRY_DSN` | 空 | 可选错误上报 |

完整模板见 `backend/.env.example`。

## 上线检查清单

- [ ] `DEBUG=False`
- [ ] 设置强随机 `SECRET_KEY`
- [ ] 配置正确的 `ALLOWED_HOSTS` 与 `CORS_ALLOWED_ORIGINS`
- [ ] 使用 PostgreSQL（而非 SQLite）并配置备份
- [ ] 配置 Redis 缓存（`CACHE_BACKEND=redis`）
- [ ] 媒体文件（`/media`）由 Nginx 或对象存储提供
- [ ] 开启 HTTPS（HSTS）
- [ ] 配置 `SENTRY_DSN` 以便错误监控
- [ ] 通过 `/api/health/` 探活（数据库 + 缓存）

## 健康检查

`GET /api/health/` 会检查数据库与缓存连通性，供容器编排 / 负载均衡探活使用。

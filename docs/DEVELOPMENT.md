# 开发指南

本指南面向希望参与开发的贡献者，覆盖环境搭建、常用命令、测试与代码质量。
贡献流程与分支/提交规范请同时阅读 [../CONTRIBUTING.md](../CONTRIBUTING.md)。

## 环境要求

- Python 3.12
- Node.js ≥ 20.19（推荐 22）
- （可选）PostgreSQL 16、Redis；不装时后端自动回退到 SQLite + LocMem

## 快速搭建

```bash
# 后端
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_demo
python manage.py runserver

# 前端（另开终端）
cd frontend
npm install
cp .env.example .env
npm run dev
```

也可以直接 `make install` / `make backend` / `make frontend`，运行 `make help` 查看全部命令。

## 常用命令（Makefile）

| 命令 | 说明 |
| --- | --- |
| `make install` | 安装前后端依赖 |
| `make migrate` / `make seed` | 数据库迁移 / 导入示例数据 |
| `make backend` / `make frontend` | 启动后端 / 前端开发服务器 |
| `make test` | 后端测试 + 前端 lint / 类型检查 |
| `make check` / `make lint` / `make format` | 系统检查 / 代码检查 / 格式化 |
| `make docker-up` / `make docker-down` | Docker Compose 启停 |

## 测试

```bash
# 后端（无需 PostgreSQL / Redis）
cd backend
DB_ENGINE=sqlite CACHE_BACKEND=locmem python manage.py test
# 带覆盖率
DB_ENGINE=sqlite CACHE_BACKEND=locmem coverage run manage.py test && coverage report -m

# 前端（Vitest）
cd frontend
npm run test            # 单次运行
npm run test:watch      # 监听模式
npm run test:coverage   # 覆盖率报告
```

测试文件约定：

- 后端：各 app 下的 `tests.py`。
- 前端：与被测代码同目录的 `*.test.ts`（如 `src/utils/poseRecognition.test.ts`）。

## 代码质量

- Python：Black（行宽 100）+ isort + flake8。
- TypeScript / Vue：Prettier + ESLint。
- 类型检查：`npm run type-check`（vue-tsc）。
- 新增接口请补充 OpenAPI 描述（drf-spectacular）与测试。

## 本地 Git 钩子

```bash
pip install pre-commit
pre-commit install --hook-type pre-commit --hook-type commit-msg
```

钩子会在提交前自动格式化后端 Python、前端 TS/Vue，并用 `commitlint` 校验
[Conventional Commits](https://www.conventionalcommits.org/) 提交信息。

## 提交规范

提交信息使用 Conventional Commits：`feat:` / `fix:` / `docs:` / `refactor:` /
`test:` / `chore:` / `ci:`。一个 PR 聚焦一件事。

## 目录速查

```
backend/   Django 应用（见 backend.md）
frontend/  Vue 3 应用（见 frontend.md）
docs/      文档（见 README.md）
scripts/   工具脚本（图标生成、pre-commit 包装脚本）
```

## 常见问题

- **AI 功能不可用**：在 `backend/.env` 配置 `CN_VLM_API_KEY` / `DEEPSEEK_API_KEY`；
  不配置不影响注册、训练记录与推荐等核心功能。
- **前端请求 404 / 跨域**：确认 Vite 已把 `/api` 代理到 `http://127.0.0.1:8000`，
  或设置 `VITE_DEV_PROXY_TARGET`。
- **迁移缺失**：CI 会执行 `makemigrations --check`，本地提交前记得生成迁移。

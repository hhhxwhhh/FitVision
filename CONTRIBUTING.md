# 贡献指南

感谢你对 FitVision 感兴趣！无论是修 Bug、补测试、改文档还是做新功能，都欢迎提交 PR。

## 开发环境

推荐使用 **Python 3.12 + Node.js 20/22 + PostgreSQL 16**。不想安装数据库时，后端会自动回退到 SQLite。

```bash
# 后端
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env          # 按需填写，可全部留空使用 SQLite
python manage.py migrate
python manage.py runserver

# 前端（另开终端）
cd frontend
npm install
cp .env.example .env
npm run dev
```

也可以直接使用 Docker：

```bash
cp .env.docker.example .env
docker compose up --build
```

## 快捷命令

仓库根目录提供 `Makefile`（Git Bash / macOS / Linux / WSL）：

```bash
make install     # 安装前后端依赖
make migrate     # 数据库迁移
make seed        # 导入示例动作与训练数据
make backend     # 启动 Django
make frontend    # 启动 Vite
make test        # 后端测试 + 前端 lint/类型检查
make docker-up   # Docker Compose 一键启动
```

运行 `make help` 可查看全部命令；Windows 下没有 `make` 时可直接执行命令本身。

## 分支与提交

- 从 `main` 创建分支：`feat/xxx`、`fix/xxx`、`docs/xxx`、`refactor/xxx`。
- 提交信息使用 [Conventional Commits](https://www.conventionalcommits.org/)：
  - `feat: 新增训练动作连击提示`
  - `fix: 修复 JWT 过期后页面空白`
  - `docs: 补充 Docker 部署说明`
  - `refactor: 拆分推荐服务`
- 一个 PR 聚焦一件事，避免混入无关格式化。

## 提交前自检

```bash
# 前端
cd frontend
npm run lint
npm run type-check
npm run build

# 后端
cd backend
DB_ENGINE=sqlite CACHE_BACKEND=locmem python manage.py check
DB_ENGINE=sqlite CACHE_BACKEND=locmem python manage.py test
```

CI 会执行同样的检查，提交前本地跑一遍能显著加快合并速度。

## 代码风格

- Python：Black（行宽 100）+ isort + flake8，配置见 `backend/pyproject.toml` 与 `setup.cfg`。
- TypeScript / Vue：Prettier + ESLint，配置见 `frontend/.prettierrc.json` 与 `frontend/eslint.config.js`。
- 新增接口请补充 OpenAPI 描述（drf-spectacular）与必要测试。
- 不要在代码或文档中写入真实密钥、数据库密码或用户数据。

## PR 检查清单

- [ ] 说明改动目的与用户可见效果
- [ ] 补充或更新测试
- [ ] 本地通过 lint、类型检查与测试
- [ ] 更新相关文档（README / docs）
- [ ] 没有提交 `.env`、模型权重缓存或构建产物

## 适合上手的贡献方向

- 为 `users` / `training` / `analytics` 补充接口测试
- MediaPipe 姿态检测的浏览器兼容性与性能优化
- 推荐算法的离线评测与可解释性
- 中英文文案统一与可访问性改进
- 部署示例（Fly.io、Railway、Kubernetes）

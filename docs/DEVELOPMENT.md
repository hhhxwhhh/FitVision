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
python manage.py seed_demo --with-history   # 生成演示用户的训练历史（可复现）
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

- 后端：各 app 下的 `tests.py`。纯算法模块可脱离 Django 直接运行，例如：

  ```bash
  cd backend
  python -m unittest recommendations.test_rerank   # MMR 重排
  python -m unittest utils.test_demo_data         # 演示数据生成器
  python -m unittest utils.test_readiness         # 训练准备度 / 负荷模型
  ```

- 前端：与被测代码同目录的 `*.test.ts`（工具与 composable）或 `*.spec.ts`
  （组件，使用 `@vitest-environment happy-dom` + `@vue/test-utils`）。

## 构建与体积预算

```bash
cd frontend
npm run build   # 先执行 vue-tsc 类型检查，再打包
npm run size    # 校验 dist 的 gzip 体积预算
```

- Element Plus 由 `unplugin-vue-components` 按模板实际用到的组件（含 `v-loading` 指令）按需引入，
  不再整体注册；`src/components.d.ts` 是插件生成的产物，请勿手动编辑。
- ECharts 同理：各视图只从 `echarts/core` 注册所需图表与组件。
- 命令行调用的组件（`ElMessage` / `ElMessageBox`）无法被模板扫描到，其样式在 `src/main.ts` 显式引入。
- `scripts/check-bundle-size.mjs` 的预算：入口 chunk 40KB、关键路径 CSS 80KB、任一 JS chunk 450KB（均按 gzip）。
  超过预算时脚本与 CI 都会失败。

## 演示数据

```bash
cd backend
python manage.py seed_demo                 # 动作库 + 示例训练计划
python manage.py seed_demo --with-history  # 再生成演示用户的训练历史
python manage.py seed_demo_history --user demo --weeks 12 --force
```

- 历史数据由 `utils/demo_data.py` 的**确定性生成器**产生，固定 `--seed` 即可复现。
- 生成内容：训练会话、每个动作的记录、交互日志以及 `UserStats` 汇总，用于首页/统计/成长展示。
- `UserExerciseRecord.created_at` / `UserInteraction.timestamp` 是 `auto_now_add`，命令通过 `update()` 回填真实历史时间。
- 负荷默认**周期化**（`week_load_factor`）：4 周一循环，前 3 周渐进超负荷、第 4 周减量；
  `periodization=False` 或 `--no-periodization` 可关掉。
- `performance_score` 按模型约定的 **0-5 分制**写入（成长 XP 里按 ×4 折算质量加成）。

### 多用户数据集（推荐算法用）

```bash
cd backend
python manage.py seed_population --users 12 --weeks 6 --seed 7   # 或 make seed-population
```

- 由 `utils/demo_data.py` 的 `generate_population` 生成：用户按初级 / 中级 / 高级轮转，目标在减脂 / 增肌 / 耐力 / 柔韧之间均衡分布。
- 每个 persona 有自己的训练频次、坚持度、起始动作评分与每周进步幅度，因此数据集中各水平的评分确实不同（实测约 64 / 74 / 82）。
- 每位用户还会写入档案、激活目标、`UserStats` 汇总与交互日志；`--force` 会先清空这些用户的历史。
- 统一密码 `fitvision123`，仅用于本地演示数据。

## 训练准备度模型

`backend/utils/readiness.py` 是纯函数、无 Django 依赖的负荷模型，可单独跑单测：

```bash
cd backend && python -m unittest utils.test_readiness
```

| 组成 | 做法 | 作用 |
| --- | --- | --- |
| Banister 冲激响应 | `Σ L·e^(-Δt/42)` 与 `Σ L·e^(-Δt/7)` | 体能 / 疲劳 / TSB（竞技状态） |
| ACWR（EWMA） | 7 天与 28 天指数移动平均之比 | 伤病风险，甜蜜区 0.8–1.3 |
| Foster 单调性 / 紧张度 | 周负荷均值 ÷ 周负荷标准差 | 训练过于单一时给出提醒 |
| 动作质量趋势 | 最近 8 次评分的最小二乘斜率 | 技术进步 / 退步 |
| 恢复间隔 | 距上次训练天数 | 0 天扣分，2 天是超量恢复窗口 |

服务端 `growth.services.readiness_snapshot` 只负责取数（`daily_training_loads` 按本地日期聚合
会话时长与表现分）并把报告拼进 `/api/growth/overview/` 的 `readiness` 字段；前端首页与成长页
消费这些指标。**修改评分规则请改引擎并补单测，不要在视图里写魔数。**

## 代码质量

- Python：Black（行宽 100）+ isort + flake8。
- TypeScript / Vue：Prettier + ESLint（`src/components.d.ts` 已忽略）。
- 类型检查：`npm run type-check`（vue-tsc）。
- 安全：模型返回的富文本一律先经 `src/utils/sanitizeHtml.ts` 消毒，禁止直接 `v-html` 原始字符串。
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

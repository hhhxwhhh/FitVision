# FitVision

**AI 驱动的个人健身教练：姿态识别 · 动作纠错 · 个性化推荐 · 训练数据分析**

[![CI](https://github.com/hhhxwhhh/FitVision/actions/workflows/ci.yml/badge.svg)](https://github.com/hhhxwhhh/FitVision/actions/workflows/ci.yml)
[![CodeQL](https://github.com/hhhxwhhh/FitVision/actions/workflows/codeql.yml/badge.svg)](https://github.com/hhhxwhhh/FitVision/actions/workflows/codeql.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Vue 3](https://img.shields.io/badge/Vue-3-42b883.svg)](https://vuejs.org/)
[![Django](https://img.shields.io/badge/Django-5.2-092e20.svg)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.12-3776ab.svg)](https://www.python.org/)

> FitVision is an AI-powered fitness coach. It uses browser-based pose estimation and
> vision-language models to score exercise form, recommends the next exercise with a
> hybrid recommendation pipeline, and turns every session into actionable analytics.
> The whole stack runs locally with one `docker compose up`.

---

## 目录

- [功能特性](#功能特性)
- [页面一览](#页面一览)
- [系统架构](#系统架构)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
- [演示数据与账号](#演示数据与账号)
- [环境变量](#环境变量)
- [API 与文档](#api-与文档)
- [测试与代码质量](#测试与代码质量)
- [项目结构](#项目结构)
- [设计要点](#设计要点)
- [路线图](#路线图)
- [文档](#文档)
- [社区](#社区)
- [贡献](#贡献)

---

## 功能特性

### AI 训练闭环

- **实时姿态识别**：浏览器端 MediaPipe Pose 识别关键点，统计次数、计算动作标准度；支持深蹲、俯卧撑、开合跳、平板支撑、弓步蹲、卷腹六种模式。
- **节奏与速度分析（VBT）**：每次动作计算用时、平均速度与节奏分类（爆发 / 控制 / 偏慢），给出教练式节奏反馈。
- **视觉大模型纠错**：关键帧上传至兼容 OpenAI 协议的视觉模型（默认豆包），生成动作问题与改进建议。
- **AI 训练计划**：结合用户画像、目标、疲劳度与器械条件生成训练计划。
- **训练报告**：本次亮点、需要改进、下一次建议，以及可继续训练的一键入口。

### 混合推荐系统

多路召回 + 加权融合，而不是单一规则：

| 引擎 | 作用 |
| --- | --- |
| DL Sequence（GRU + Attention） | 基于最近训练序列预测下一个动作 |
| Knowledge Graph（GCN） | 沿前置依赖与相似用户路径推荐 |
| Content-Based（M3E + Chroma） | 语义相似动作检索 |
| RL Adaptive | 根据疲劳与历史表现动态调节 |
| Time-Travel CF | 冷启动阶段匹配相似体质用户 |
| Cold Start | 热门动作兜底 |

召回后会继续做**目标导向重排**（减脂 / 增肌）、**疲劳联动抑制**、基于 **MMR（最大边际相关）**
的**相关性与多样性平衡重排**、**自适应探索**，并保留前置动作解锁校验。

### 成长与激励

- **经验与等级**：每次训练按时长、动作质量与连续天数结算 XP，自动升级并解锁称号。
- **每日任务**：按日期确定性生成 3 个任务，进度实时计算，完成后手动领取经验。
- **限时挑战**：周挑战与月挑战按周期自动刷新，先参加再领取，进度直接取自训练数据。
- **本周目标**：可自定义每周训练天数与分钟数，达成后领取周奖励。
- **成就系统**：里程碑、连续性、训练量、动作质量、探索与特别成就，服务端统一判定。
- **个人纪录**：自动记录每个动作的最大重量、最高次数、单次容量与最佳评分。
- **本周经验榜**：赛季制周榜，支持公开/隐身切换，昵称脱敏展示。
- **状态就绪度**：服务端结合疲劳、连续天数与本周节奏给出今日训练建议。
- 动作知识图谱与前置解锁，训练路径一目了然。
- 数据中心展示训练量、卡路里、动作标准度趋势。

### 现代 Web 体验

- Vue 3 + TypeScript + Element Plus，路由级代码分割。
- **统一设计系统**：`--fv-*` 设计令牌、明暗双主题、跟随系统偏好、首屏无闪烁。
- **全局命令面板**：`Ctrl/⌘ + K` 搜索动作、跳转页面、切换主题。
- **训练状态驾驶舱**：今日状态评分、AI 教练洞察、本周节奏与成就进度。
- **成长中心**：等级进度、每日任务、限时挑战、成就墙、个人纪录与本周经验榜。
- **训练历史时间线**：按月分组回看每一次训练，支持完成状态筛选与分页加载。
- **可安装 PWA**：离线应用外壳、桌面/移动端安装、快捷方式、在线状态提示。
- **数据导出**：训练统计一键导出 CSV，方便二次分析。
- JWT 自动续期、401 统一跳转、响应式布局、减少动效偏好支持。

---

## 页面一览

| 路由 | 页面 | 说明 |
| --- | --- | --- |
| `/` | 首页驾驶舱 | 今日状态、本周节奏、成就进度与快捷入口 |
| `/training` | 智能训练 | 姿态识别、实时计数、动作评分与语音教练 |
| `/training/report` | 训练报告 | 本次亮点、改进建议与下一步推荐 |
| `/ai-plan` | AI 训练计划 | 结合画像、目标与器械生成训练计划 |
| `/history` | 训练历史 | 按月分组的时间线，完成状态筛选与分页 |
| `/analytics` | 数据中心 | 训练量、卡路里与动作质量趋势 |
| `/growth` | 成长中心 | 等级、任务、挑战、成就与周榜 |
| `/exercises` | 动作百科 | 动作库检索与筛选 |
| `/exercises/graph` | 知识图谱 | 前置依赖与训练路径 |
| `/posture-diagnosis` | 姿态诊断 | 视觉大模型动作纠错 |
| `/profile` | 个人中心 | 档案、目标与偏好 |

> 未登录访问受保护页面会跳转到 `/login`。按 `?` 打开快捷键面板，`Ctrl / ⌘ + K` 打开命令面板。

---

## 系统架构

```mermaid
flowchart LR
    subgraph Browser
        Vue[Vue 3 + TypeScript]
        MP[MediaPipe Pose]
        PWA[Service Worker / PWA]
    end

    subgraph Django["Django 5 + DRF"]
        Auth[JWT 认证 / 限流]
        Exercise[动作库 / 知识图谱]
        Training[训练会话 / 报告]
        Rec[混合推荐]
        VLM[VLM 服务]
        Health[健康检查]
    end

    subgraph Data
        PG[(PostgreSQL / SQLite)]
        Redis[(Redis Cache / Celery)]
        Chroma[(Chroma 向量库)]
    end

    LLM[DeepSeek / 视觉大模型]

    Vue -->|REST /api| Auth
    Vue --> Exercise
    Vue --> Training
    Vue --> Rec
    MP -->|姿态关键点| Vue
    VLM --> LLM
    Training --> VLM
    Rec --> Chroma
    Rec --> PG
    Exercise --> PG
    Auth --> Redis
    Health --> PG
    Health --> Redis
```

---

## 技术栈

| 层 | 技术 |
| --- | --- |
| 前端 | Vue 3、TypeScript、Vite 7、Pinia、Vue Router、Element Plus、ECharts、MediaPipe Pose |
| 后端 | Python 3.12、Django 5.2、Django REST Framework、SimpleJWT、drf-spectacular |
| AI / 推荐 | PyTorch、GCN、GRU + Attention、scikit-learn、Chroma、sentence-transformers（M3E） |
| 数据 | PostgreSQL 16（生产）/ SQLite（开发与测试）、Redis、Celery |
| 工程化 | ESLint 9、Prettier、Black、isort、flake8、GitHub Actions、Docker Compose |

> 机器学习依赖（torch / chromadb / sentence-transformers）采用**按需加载**：
> 未安装时项目仍可启动，非 AI 接口与测试不受影响。

---

## 快速开始

### 方式一：Docker Compose（推荐）

```bash
git clone https://github.com/hhhxwhhh/FitVision.git
cd FitVision

cp .env.docker.example .env
# 编辑 .env：至少设置 SECRET_KEY 与 DB_PASSWORD

docker compose up --build
```

| 服务 | 地址 |
| --- | --- |
| 前端 | http://localhost:8080 |
| API 根 | http://localhost:8000/api/ |
| Swagger 文档 | http://localhost:8000/api/docs/ |
| 健康检查 | http://localhost:8000/api/health/ |

> 首次构建需要下载 PyTorch（CPU 版）与向量模型，耗时较长；后续启动会复用缓存。

### 方式二：本地开发

**环境要求**：Python 3.12、Node.js ≥ 20.19（推荐 22）。数据库可省略，后端会自动使用 SQLite。

```bash
# 1. 后端
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS / Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env              # 可全部留空，使用 SQLite + LocMem
python manage.py migrate
python manage.py seed_demo        # 自动导入动作库与示例训练计划（已有数据时跳过）
python manage.py seed_demo --with-history   # 可选：再生成演示用户的训练历史
python manage.py runserver

# 2. 前端（另开终端）
cd frontend
npm install
cp .env.example .env
npm run dev
```

打开 http://localhost:5173 。Vite 会将 `/api` 与 `/media` 代理到 `http://127.0.0.1:8000`。

> 需要 AI 诊断功能时，在 `backend/.env` 中配置 `CN_VLM_API_KEY`（视觉模型）与
> `DEEPSEEK_API_KEY`（文本 / 计划生成）。不配置不影响注册、训练记录与推荐等核心功能。

### 演示数据与演示账号

想直接看到"有数据"的效果，可生成一套**可复现**的演示数据：

```bash
cd backend
python manage.py seed_demo --with-history
```

- 演示账号：`demo` / `fitvision123`（仅用于本地演示，请勿用于生产）。
- 生成内容：8 周训练历史（会话、动作记录、交互）与用户统计；固定 `--seed` 即可复现。
- 参数可调：`python manage.py seed_demo_history --weeks 12 --days-per-week 5 --force`。

> 历史数据由 `backend/utils/demo_data.py` 的确定性生成器产生，
> 测试可用 `python -m unittest utils.test_demo_data`。

---

## 环境变量

### 后端（`backend/.env`）

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DEBUG` | `True` | 生产环境必须为 `False` |
| `SECRET_KEY` | 开发用临时值 | 生产环境必填，建议随机 50+ 字符 |
| `ALLOWED_HOSTS` | `127.0.0.1,localhost` | 逗号分隔 |
| `CORS_ALLOWED_ORIGINS` | 本地 5173 / 8080 | 逗号分隔的前端源 |
| `DB_NAME` | 空 | 留空使用 SQLite；填写则连接 PostgreSQL |
| `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | — | PostgreSQL 连接信息 |
| `CACHE_BACKEND` | `locmem` | `locmem` 或 `redis` |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | 缓存与 Celery |
| `DEEPSEEK_API_KEY` | 空 | 文本生成 / 计划 |
| `CN_VLM_API_KEY` | 空 | 视觉模型 API Key |
| `CN_VLM_MODEL` / `CN_VLM_BASE_URL` | 豆包 / OpenKey | OpenAI 兼容接口 |
| `SENTRY_DSN` | 空 | 可选错误上报 |
| `THROTTLE_ANON` / `THROTTLE_USER` / `THROTTLE_AUTH` | `60/min` / `600/min` / `10/min` | 限流 |
| `HF_ENDPOINT` | `https://hf-mirror.com` | 向量模型下载镜像 |

完整模板见 [`backend/.env.example`](backend/.env.example)。

### 前端（`frontend/.env`）

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `VITE_API_BASE_URL` | `/api` | 生产环境可填完整地址 |
| `VITE_DEV_PROXY_TARGET` | `http://127.0.0.1:8000` | 开发代理目标 |

---

## API 与文档

- Swagger UI：`/api/docs/`
- OpenAPI Schema：`/api/schema/`
- 健康检查：`GET /api/health/`（检查数据库与缓存，供容器 / 负载均衡探活）
- 令牌刷新：`POST /api/auth/refresh/`

主要路由：

```
/api/auth/            注册、登录、刷新、用户档案、目标、统计
/api/exercises/       动作库、分类、知识图谱、训练记录
/api/training/        训练会话、计划、报告、AI 分析
/api/recommendations/ 个性化推荐与反馈
/api/analytics/       训练数据分析
/api/growth/          等级、每日任务、限时挑战、周目标、成就、个人纪录、排行榜
/api/ai/              姿态诊断 / VLM 分析
```

---

## 测试与代码质量

```bash
# 后端（无需 PostgreSQL / Redis）
cd backend
DB_ENGINE=sqlite CACHE_BACKEND=locmem python manage.py check
DB_ENGINE=sqlite CACHE_BACKEND=locmem python manage.py test
DB_ENGINE=sqlite CACHE_BACKEND=locmem coverage run manage.py test && coverage report -m

# 前端
cd frontend
npm run lint
npm run type-check
npm run build
npm run test            # Vitest 单元测试
npm run test:coverage   # 覆盖率报告
```

CI 会在每次 Push / PR 时执行以上检查（含前后端测试覆盖率），并验证 Docker
Compose 镜像构建。另有 CodeQL 安全扫描与依赖自动更新（Dependabot）。本地可用
`pre-commit` 钩子在提交前自动格式化与校验，详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## 项目结构

```text
FitVision/
├── backend/
│   ├── fitvision/          # 配置、URL、健康检查
│   ├── users/              # 认证、档案、目标、统计
│   ├── exercises/          # 动作库、分类、知识图谱
│   ├── training/           # 训练会话、计划、报告
│   ├── recommendations/    # 多引擎混合推荐
│   ├── analytics/          # 数据统计
│   ├── growth/             # 等级、任务、挑战、成就、纪录与排行榜
│   ├── ai_models/          # VLM 与姿态诊断
│   ├── utils/              # 向量库等基础设施
│   ├── requirements*.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/            # axios 客户端、自动刷新、媒体地址
│   │   ├── components/     # 通用组件与姿态预览
│   │   ├── composables/    # 姿态检测、诊断逻辑
│   │   ├── layouts/        # 应用外壳
│   │   ├── router/         # 懒加载路由与守卫
│   │   ├── stores/         # Pinia
│   │   └── views/          # 页面
│   ├── public/             # PWA manifest、Service Worker、图标
│   ├── Dockerfile
│   └── nginx.conf
├── docs/                   # 架构 / 开发 / 部署文档（见 docs/README.md）
├── scripts/                # 资源生成与 pre-commit 包装脚本
├── .github/                # CI、CodeQL、发布、labeler、stale、ISSUE/PR 模板
├── docker-compose.yml
├── .pre-commit-config.yaml # 本地 Git 钩子（格式化 + commitlint）
├── CHANGELOG.md            # 版本变更记录
├── CONTRIBUTING.md
├── GOVERNANCE.md
├── SUPPORT.md
├── SECURITY.md
└── LICENSE
```

---

## 设计要点

- **安全优先**：密钥只存在于 `.env`；生产强制随机 `SECRET_KEY`；JWT + 限流；
  CORS / CSRF / HSTS / X-Frame-Options 可配置；容器以环境变量注入配置。
- **可降级**：SQLite / LocMem / 可选 ML 依赖均有回退路径，新贡献者无需完整 ML 环境即可跑通测试。
- **可解释推荐**：每个推荐结果都带有来源标签与推荐理由，前端展示“为什么推荐它”。
- **体验细节**：路由级懒加载、PWA 离线外壳、自动令牌续期、减少动效偏好、统一焦点样式。

---

## 路线图

- [ ] 使用 MediaPipe Tasks Vision（WASM）替换旧版 Pose 方案
- [ ] WebSocket 实时训练会话与多端同步
- [ ] 推荐算法离线评测集与 A/B 实验框架
- [ ] 中英文 i18n 与完整无障碍（a11y）审计
- [ ] 移动端封装（Capacitor / React Native）
- [ ] 更多端到端测试与性能预算

---

## 文档

完整文档索引见 [`docs/README.md`](docs/README.md)：

- [架构说明](docs/ARCHITECTURE.md) · [数据流](docs/data_flow.md)
- [开发指南](docs/DEVELOPMENT.md) · [部署指南](docs/DEPLOYMENT.md)
- [本地运行](docs/run_guide.md) · [使用说明](docs/使用说明.md)

## 社区

- [贡献指南](CONTRIBUTING.md) · [行为准则](CODE_OF_CONDUCT.md) · [治理](GOVERNANCE.md)
- [获取帮助](SUPPORT.md) · [变更记录](CHANGELOG.md) · [安全策略](SECURITY.md)

## 贡献

欢迎提交 Issue 与 PR！请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 与
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。安全问题请按 [SECURITY.md](SECURITY.md) 私密报告。
建议安装 pre-commit 钩子（见贡献指南），提交信息遵循 Conventional Commits。

## License

[MIT](LICENSE) © 2026 FitVision contributors

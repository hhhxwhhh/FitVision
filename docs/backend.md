# 后端项目文档 (Backend Documentation)
该基于**Django** + **Django Rest Framework(DRF)**构建，并集成了AI服务。

## 目录结构概览

```
backend/
├── ai_models/           # AI 模型与 VLM 集成
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── serializers.py
│   ├── tests.py
│   ├── urls.py
│   ├── views.py         # 处理 AI 分析请求
│   ├── vlm_service.py   # 调用视觉大模型服务
│   └── migrations/
│       ├── __init__.py
│       ├── 0001_initial.py
│       └── 0002_posturediagnosis.py
├── analytics/           # 数据分析模块
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── serializers.py
│   ├── signals.py
│   ├── tests.py
│   ├── urls.py
│   ├── views.py
│   └── migrations/
│       ├── __init__.py
│       └── 0001_initial.py
├── exercises/           # 动作库管理
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py        # 动作数据模型
│   ├── serializers.py
│   ├── tests.py
│   ├── urls.py
│   ├── views.py
│   ├── fixtures/
│   │   └── data.json
│   ├── management/      # 自定义命令 (导入数据等)
│   │   ├── __init__.py
│   │   └── commands/
│   │       ├── __init__.py
│   │       ├── build_vectors.py
│   │       ├── generate_progression.py
│   │       └── generate_tags.py
│   └── migrations/
│       ├── __init__.py
│       ├── 0001_initial.py
│       ├── 0002_exercisecategory_demo_gif.py
│       ├── 0003_remove_exercisecategory_demo_gif_exercise_demo_gif.py
│       ├── 0004_exercisecategory_level_and_more.py
│       ├── 0005_remove_exercisecategory_level_and_more.py
│       └── 0006_exercise_tags.py
├── fitvision/           # 核心配置
│   ├── __init__.py
│   ├── asgi.py
│   ├── celery.py
│   ├── settings.py      # 项目设置 (DB, Installed Apps)
│   ├── urls.py          # 全局路由分发
│   └── wsgi.py
├── recommendations/     # 个性化推荐系统
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── dl_models.py
│   ├── gnn_models.py
│   ├── initialize_weights.py
│   ├── model_utils.py
│   ├── models.py
│   ├── serializers.py
│   ├── services.py      # 混合推荐算法逻辑
│   ├── signals.py
│   ├── tests.py
│   ├── urls.py
│   ├── views.py         # 推荐 API 视图
│   ├── management/
│   │   └── commands/
│   │       ├── generate_test_interactions.py
│   │       ├── process_rec_data.py
│   │       ├── seed_interactions.py
│   │       ├── sync_knowledge_graph_data.py
│   │       ├── train_gnn.py
│   │       └── train_rec_models.py
│   └── migrations/
│       ├── __init__.py
│       ├── 0001_initial.py
│       ├── 0002_alter_recommendedexercise_algorithm.py
│       ├── 0003_userstate_target_intensity.py
│       └── 0004_alter_recommendedexercise_algorithm.py
├── growth/              # 成长体系：等级、任务、成就、个人纪录、周榜
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py        # UserProgress / Achievement / UserDailyQuest / WeeklyGoal / PersonalRecord / XPEvent
│   ├── serializers.py
│   ├── services.py      # XP、等级、连续天数、任务进度与成就判定
│   ├── signals.py       # 训练完成后统一结算
│   ├── tests.py
│   ├── urls.py
│   ├── views.py
│   └── migrations/
│       ├── __init__.py
│       ├── 0001_initial.py
│       └── 0002_seed_achievements.py
├── training/            # 训练记录与计划
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py        # 训练日志模型
│   ├── serializers.py
│   ├── services.py
│   ├── tests.py
│   ├── urls.py
│   ├── views.py         # 训练 API
│   ├── fixtures/
│   │   └── seed.json
│   └── migrations/
│       ├── __init__.py
│       ├── 0001_initial.py
│       └── 0002_usertrainingsession_ai_analysis_and_more.py
├── users/               # 用户认证与管理
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py        # 用户扩展模型
│   ├── serializers.py
│   ├── tests.py
│   ├── urls.py
│   ├── views.py         # 登录注册 API
│   └── migrations/
│       ├── __init__.py
│       ├── 0001_initial.py
│       ├── 0002_userprofile_activity_level_userprofile_bmi_and_more.py
│       └── 0003_userprofile_avatar.py
├── utils/               # 通用工具 (向量数据库等)
│   ├── __init__.py
│   └── vector_db.py
├── generate_test_data.py    # 生成测试数据的脚本
├── manage.py            # Django 管理脚本
└── requirements.txt     # Python 依赖列表

```

## 核心模块详解

### 1. AI 视觉分析 (`ai_models`)

该模块负责与视觉大模型 (VLM) 交互，处理姿态诊断请求。

*   **[views.py](file:///d:/code/forvue/FitVision/backend/ai_models/views.py)**
    *   `VLMAnalysisAPIView`: 异步 API 视图，接收 Base64 图片，调用 `ChinaVLMService` 进行分析。支持 `realtime` (实时纠错) 和 `diagnosis` (详细报告) 模式。
    *   `PostureDiagnosisViewSet`: 管理用户的姿态诊断记录。
*   **[vlm_service.py](file:///d:/code/forvue/FitVision/backend/ai_models/vlm_service.py)**
    *   封装了对外部 VLM API 的调用逻辑，包含重试机制和结果解析。

### 2. 用户管理 (`users`)

负责用户认证和资料管理，基于 Django 自带的 Auth 系统扩展。

*   **[views.py](file:///d:/code/forvue/FitVision/backend/users/views.py)**
    *   `RegisterView`: 用户注册。
    *   `LoginView`: 用户登录，返回 JWT Token (Access + Refresh)。
    *   `ProfileView`: 获取和更新用户详细资料 (身高、体重、偏好)。

### 3. 推荐系统 (`recommendations`)

核心业务逻辑，根据用户状态和历史数据生成个性化训练计划。

*   **[views.py](file:///d:/code/forvue/FitVision/backend/recommendations/views.py)**
    *   `RecommendationViewSet`: 获取推荐动作列表。
    *   `feedback`: 记录用户对推荐结果的反馈 (Like/Dislike)，用于优化后续推荐。
*   **[services.py](file:///d:/code/forvue/FitVision/backend/recommendations/services.py)**
    *   `HybridRecommender`: 混合推荐引擎，结合基于规则 (Rules) 和协同过滤 (CF) 的算法。

### 4. 训练管理 (`training`)

记录用户的每一次训练数据。

*   **[models.py](file:///d:/code/forvue/FitVision/backend/training/models.py)**
    *   `TrainingLog`: 存储训练详情 (动作、次数、重量、消耗卡路里)。
*   **[views.py](file:///d:/code/forvue/FitVision/backend/training/views.py)**
    *   `TrainingLogView`: 创建和查询训练日志。

### 5. 成长体系 (`growth`)

将训练数据转化为可持续的激励闭环。所有发奖使用 `XPEvent` 唯一约束保证幂等，
重复保存训练会话不会重复加经验；任务与周目标进度在读取时实时计算，避免缓存漂移。

*   **[models.py](file:///d:/code/forvue/FitVision/backend/growth/models.py)**
    *   `UserProgress`: XP、等级、连续/最长训练天数、本周榜公开开关。
    *   `Achievement` / `UserAchievement`: 成就定义与解锁记录，由数据迁移写入 16 项默认成就。
    *   `UserDailyQuest`: 每个用户每天确定性生成 3 个任务。
    *   `WeeklyGoal`: 每周训练天数与分钟目标。
    *   `PersonalRecord`: 每个动作的最大重量、最高次数、单次容量与最佳评分。
    *   `XPEvent`: 经验流水，作为幂等发奖凭据。
*   **[services.py](file:///d:/code/forvue/FitVision/backend/growth/services.py)**
    *   `record_session_completed()`: 训练完成后的统一结算入口。
    *   `refresh_user_stats()`: 从训练会话重算 `UserStats`，修复统计滞后。
    *   `evaluate_achievements()`: 根据实时指标批量解锁成就。
    *   `weekly_leaderboard()`: 本周经验榜，支持昵称脱敏与隐身。
*   **[views.py](file:///d:/code/forvue/FitVision/backend/growth/views.py)**
    *   `GET /api/growth/overview/`: 成长总览（等级、就绪度、任务、周目标、成就与纪录）。
    *   `GET /api/growth/achievements/`: 成就列表与进度。
    *   `GET /api/growth/quests/`、`POST /api/growth/quests/<id>/claim/`: 每日任务与领奖。
    *   `GET/PUT /api/growth/weekly-goal/`、`POST /api/growth/weekly-goal/claim/`: 周目标与领奖。
    *   `GET /api/growth/records/`: 个人纪录。
    *   `GET /api/growth/leaderboard/`、`GET/PUT /api/growth/settings/`: 周榜与公开设置。

### 6. 全局配置 (`fitvision`)

*   **[urls.py](file:///d:/code/forvue/FitVision/backend/fitvision/urls.py)**
    *   定义了 `/api/` 下的所有路由前缀：
        *   `/api/auth/` -> `users`
        *   `/api/ai/` -> `ai_models`
        *   `/api/training/` -> `training`
        *   `/api/recommendations/` -> `recommendations`
        *   `/api/analytics/` -> `analytics`
        *   `/api/growth/` -> `growth`

## 技术栈

*   **框架**: Django 5.2 + Django Rest Framework
*   **数据库**: PostgreSQL (推荐) 或 SQLite (开发)
*   **认证**: Simple JWT (JSON Web Token)
*   **异步支持**: ADRF (Async Django Rest Framework) 用于 AI 接口
*   **API 文档**: drf-spectacular (Swagger UI)

---
*文档生成时间: 2026-03-07*

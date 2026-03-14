# 后端项目文档 (Backend Documentation)

本文档详细介绍了 FitVision 后端项目的目录结构、关键模块及其功能。该项目基于 **Django** + **Django Rest Framework (DRF)** 构建，并集成了 AI 服务。

## 📁 目录结构概览

```
backend/
├── ai_models/           # 🤖 AI 模型与 VLM 集成
│   ├── views.py         # 处理 AI 分析请求
│   └── vlm_service.py   # 调用视觉大模型服务
├── analytics/           # 📊 数据分析模块
├── exercises/           # 🏋️ 动作库管理
│   ├── models.py        # 动作数据模型
│   └── management/      # 自定义命令 (导入数据等)
├── fitvision/           # ⚙️ 核心配置
│   ├── settings.py      # 项目设置 (DB, Installed Apps)
│   └── urls.py          # 全局路由分发
├── recommendations/     # 🎯 个性化推荐系统
│   ├── services.py      # 混合推荐算法逻辑
│   └── views.py         # 推荐 API 视图
├── training/            # 📝 训练记录与计划
│   ├── models.py        # 训练日志模型
│   └── views.py         # 训练 API
├── users/               # 👤 用户认证与管理
│   ├── models.py        # 用户扩展模型
│   └── views.py         # 登录注册 API
├── utils/               # 🛠️ 通用工具 (向量数据库等)
├── manage.py            # Django 管理脚本
└── requirements.txt     # Python 依赖列表
```

## 🧩 核心模块详解

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

### 5. 全局配置 (`fitvision`)

*   **[urls.py](file:///d:/code/forvue/FitVision/backend/fitvision/urls.py)**
    *   定义了 `/api/` 下的所有路由前缀：
        *   `/api/auth/` -> `users`
        *   `/api/ai/` -> `ai_models`
        *   `/api/training/` -> `training`
        *   `/api/recommendations/` -> `recommendations`

## 🛠️ 技术栈

*   **框架**: Django 4.x + Django Rest Framework
*   **数据库**: PostgreSQL (推荐) 或 SQLite (开发)
*   **认证**: Simple JWT (JSON Web Token)
*   **异步支持**: ADRF (Async Django Rest Framework) 用于 AI 接口
*   **API 文档**: drf-spectacular (Swagger UI)

---
*文档生成时间: 2026-03-07*

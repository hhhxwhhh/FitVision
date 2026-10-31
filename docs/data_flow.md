# 前后端数据流动文档 (Data Flow Documentation)

本文档详细描述了 FitVision 系统中关键业务场景的数据流动过程。

## 用户认证流程 (Authentication Flow)

用户登录和获取 Token 的过程。

1.  **用户输入**: 用户在前端 `LoginView` 输入用户名和密码。
2.  **前端请求**: `userStore.login()` 调用 Axios 发送 POST 请求到 `/api/auth/login/`。
3.  **后端验证**:
    *   Django 接收请求，`LoginView` 解析数据。
    *   调用 `authenticate()` 验证凭据。
    *   验证成功，生成 JWT `access` 和 `refresh` Token。
4.  **响应**: 后端返回 Token 给前端。
5.  **前端存储**:
    *   `userStore` 将 Token 存入 `localStorage`。
    *   设置 `isAuthenticated = true`。
    *   后续所有 API 请求都会在 Header 中携带 `Authorization: Bearer <access_token>`。

## AI 姿态诊断流程 (AI Diagnosis Flow)

从摄像头采集到生成诊断报告的全过程。

1.  **视频流采集 (前端)**:
    *   用户进入 `PostureDiagnosisView`。
    *   `usePoseDetection` 初始化 MediaPipe，开启摄像头。
    *   MediaPipe 在本地浏览器实时检测人体 33 个关键点 (Landmarks)。
2.  **触发分析 (前端)**:
    *   用户点击“一键扫描分析”。
    *   前端调用 `canvas.toDataURL()` 截取当前视频帧 (Base64)。
    *   前端发送 POST 请求到 `/api/ai/analyze/`，携带 Base64 图片和模式 (`diagnosis`)。
3.  **异步处理 (后端)**:
    *   `VLMAnalysisAPIView` (Async) 接收请求。
    *   后端调用 `ChinaVLMService` 将图片发送给视觉大模型 (VLM)。
    *   VLM 分析图片，返回体态问题描述和改善建议。
4.  **关联推荐 (后端)**:
    *   后端根据 VLM 返回的“目标肌群”建议，查询数据库中的 `Exercise` 表。
    *   筛选出最匹配的动作 (如：圆肩 -> 推荐面拉)。
5.  **结果返回**: 后端将 VLM 分析结果 + 推荐动作列表打包返回给前端。
6.  **展示报告 (前端)**: `PostureDiagnosisView` 渲染诊断报告和推荐动作。

## 训练与记录流程 (Training & Logging Flow)

用户进行锻炼并记录数据的过程。

1.  **动作识别 (前端)**:
    *   用户在 `TrainingView` 开始训练。
    *   `usePoseDetection` 实时计算关节角度 (如膝盖角度)。
    *   根据角度变化 (State Machine: UP -> DOWN -> UP) 自动计数。
2.  **数据汇总 (前端)**:
    *   训练结束，前端汇总：动作名称、总次数、总耗时。
    *   根据用户体重估算卡路里消耗。
3.  **提交记录 (前端)**:
    *   训练过程中，前端通过 `POST /api/training/exercise-records/` 逐条写入动作记录。
    *   训练结束后，前端通过 `PUT /api/training/sessions/<id>/complete/` 提交自评与卡路里。
4.  **保存与更新 (后端)**:
    *   `complete_training_session` 调用 AI 教练生成综合评分与分析报告，并保存会话。
    *   `UserTrainingSession` 的 `post_save` 信号触发成长体系结算。
    *   `analytics` 信号重算当日 `UserDailyStats` 与动作 `ExerciseProgress`。
    *   推荐系统根据最近训练更新疲劳度与部位训练容量。

## 成长结算流程 (Growth Flow)

1.  **触发结算**: 会话标记为已完成时，`growth.signals` 调用 `record_session_completed()`。
2.  **进度重算**: 从全部已完成会话重新计算连续天数、最长连续、累计训练次数与最近训练日期。
3.  **经验发放**: 按「基础分 + 时长 + 动作质量 + 连续奖励」计算 XP，并写入 `XPEvent`。
    `(user, source, reference_id)` 唯一约束保证同一会话只结算一次。
4.  **个人纪录**: 扫描本次会话的动作记录，刷新最大重量、最高次数、单次容量与最佳评分。
5.  **统计修复**: `refresh_user_stats()` 从会话重新计算 `UserStats`，避免首页统计滞后。
6.  **成就判定**: 汇总训练次数、连续天数、总容量、动作种类等指标，解锁新成就并发放 XP。
7.  **任务与周目标**: 读取 `GET /api/growth/overview/` 时实时计算今日任务与本周目标进度；
    用户在成长中心手动领取任务/周目标奖励。
8.  **限时挑战**: 用户通过 `POST /api/growth/challenges/<id>/join/` 参加当前周期挑战；
    读取时按周/月窗口从训练会话与动作记录实时计算进度，完成后
    `POST /api/growth/challenges/<id>/claim/` 领取经验，`XPEvent` 保证同一参赛记录只结算一次。
9.  **周榜**: `GET /api/growth/leaderboard/` 聚合本周 `XPEvent`，按经验排序并脱敏展示昵称。

## 个性化推荐流程 (Recommendation Flow)

1.  **请求推荐 (前端)**:
    *   用户进入首页或 `AIPlanView`。
    *   前端请求 `/api/recommendations/get_personalized/`。
2.  **混合计算 (后端)**:
    *   `HybridRecommender` 读取用户画像 (目标、伤病史)。
    *   读取用户最近的训练记录 (判断疲劳度)。
    *   结合协同过滤 (相似用户的选择) 生成推荐列表。
3.  **返回列表**: 后端返回一组推荐的 `Exercise` 对象。

---
*文档生成时间: 2026-03-07*

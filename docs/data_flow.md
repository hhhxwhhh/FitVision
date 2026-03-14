# 前后端数据流动文档 (Data Flow Documentation)

本文档详细描述了 FitVision 系统中关键业务场景的数据流动过程。

## 🔐 用户认证流程 (Authentication Flow)

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

## 🤖 AI 姿态诊断流程 (AI Diagnosis Flow)

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

## 🏋️ 训练与记录流程 (Training & Logging Flow)

用户进行锻炼并记录数据的过程。

1.  **动作识别 (前端)**:
    *   用户在 `TrainingView` 开始训练。
    *   `usePoseDetection` 实时计算关节角度 (如膝盖角度)。
    *   根据角度变化 (State Machine: UP -> DOWN -> UP) 自动计数。
2.  **数据汇总 (前端)**:
    *   训练结束，前端汇总：动作名称、总次数、总耗时。
    *   根据用户体重估算卡路里消耗。
3.  **提交记录 (前端)**:
    *   前端发送 POST 请求到 `/api/training/logs/`。
4.  **保存与更新 (后端)**:
    *   `TrainingLogView` 接收数据并保存到 `TrainingLog` 表。
    *   后端触发信号 (Signal)，更新用户的 `UserStats` (总训练时长、总消耗)。
    *   更新推荐系统的用户状态 (如：今日已练腿，明日推荐练胸)。

## 🎯 个性化推荐流程 (Recommendation Flow)

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

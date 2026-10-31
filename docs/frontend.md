# 前端项目文档 (Frontend Documentation)

本文档详细介绍了 FitVision 前端项目的目录结构、关键文件及其作用。该项目基于 **Vue 3** + **TypeScript** + **Vite** 构建，并集成了 **MediaPipe** 进行实时姿态检测。

## 目录结构概览

```
frontend/
├── public/              # 静态资源目录
├── src/                 # 源代码目录
│   ├── api/             # API 接口定义与 Axios 封装
│   ├── assets/          # 静态资源 (图片、样式等)
│   ├── components/      # 公共 UI 组件
│   ├── composables/     # 组合式 API (核心逻辑)
│   ├── layouts/         # 页面布局组件
│   ├── router/          # 路由配置
│   ├── services/        # 业务服务层
│   ├── stores/          # Pinia 状态管理
│   ├── utils/           # 工具函数
│   ├── views/           # 页面视图
│   ├── App.vue          # 根组件
│   ├── main.ts          # 入口文件
│   └── style.css        # 全局样式
├── index.html           # HTML 模板
├── package.json         # 项目依赖与脚本
├── tsconfig.json        # TypeScript 配置
└── vite.config.ts       # Vite 构建配置
```

## 关键文件详解

### 1. 核心逻辑 (Composables)

*   **[usePoseDetection.ts](file:///d:/code/forvue/FitVision/frontend/src/composables/usePoseDetection.ts)**
    *   **作用**: 封装了 MediaPipe Pose 的核心逻辑。
    *   **功能**:
        *   初始化摄像头和 Pose 模型。
        *   使用 OneEuroFilter 平滑人体关键点，并交给 `poseRecognition` 引擎分析。
        *   实现动作计数、阶段切换、动作质量评分与实时纠错提示。
        *   输出识别置信度、视角（正面/侧面）与当前生效的错误标签。
        *   提供 AI 语音指导 (Text-to-Speech)。
        *   提供 `captureFrameBase64` 方法用于截图分析。

*   **[usePostureDiagnosis.ts](file:///d:/code/forvue/FitVision/frontend/src/composables/usePostureDiagnosis.ts)**
    *   **作用**: 处理姿态诊断相关的业务逻辑。

### 2. 页面视图 (Views)

*   **[PostureDiagnosisView.vue](file:///d:/code/forvue/FitVision/frontend/src/views/PostureDiagnosisView.vue)**
    *   **作用**: 姿态诊断页面。
    *   **功能**:
        *   调用摄像头预览。
        *   用户点击“一键扫描分析”后，捕获当前帧并发送给后端。
        *   展示 VLM (视觉大模型) 返回的诊断报告，包括体态问题、改善建议和推荐动作。

*   **[TrainingView.vue](file:///d:/code/forvue/FitVision/frontend/src/views/TrainingView.vue)**
    *   **作用**: 训练页面。
    *   **功能**: 用户跟随视频或 AI 指导进行锻炼，实时显示计数和消耗。

*   **[GrowthView.vue](file:///d:/code/forvue/FitVision/frontend/src/views/GrowthView.vue)**
    *   **作用**: 成长中心页面。
    *   **功能**:
        *   展示等级环、XP 进度、连续训练天数与累计训练次数。
        *   每日任务列表，完成后领取经验。
        *   周/月限时挑战，支持参加挑战、查看周期进度与领取奖励。
        *   成就墙，支持按分类筛选并展示进度。
        *   本周目标编辑与领奖、个人纪录、本周经验榜。
        *   周榜公开/隐身切换，昵称由后端脱敏返回。

*   **[LoginView.vue](file:///d:/code/forvue/FitVision/frontend/src/views/LoginView.vue) / [RegisterView.vue](file:///d:/code/forvue/FitVision/frontend/src/views/RegisterView.vue)**
    *   **作用**: 用户登录和注册页面。

### 3. 状态管理 (Stores)

*   **[userStore.ts](file:///d:/code/forvue/FitVision/frontend/src/stores/userStore.ts)**
    *   **作用**: 管理用户认证状态和基本信息。
    *   **功能**:
        *   `login()`: 调用登录接口，保存 JWT Token。
        *   `fetchUser()`: 获取当前用户信息。
        *   `logout()`: 清除 Token 并重置状态。

### 4. API 通信

*   **[api/index.ts](file:///d:/code/forvue/FitVision/frontend/src/api/index.ts)**
    *   **作用**: Axios 实例配置。
    *   **配置**:
        *   Base URL: `http://127.0.0.1:8000/api`
        *   请求拦截器: 自动在 Header 中添加 `Authorization: Bearer <token>`。
        *   响应拦截器: 处理 401 未授权错误 (自动登出)。

### 5. 工具类 (Utils)

*   **[poseRecognition.ts](file:///d:/code/forvue/FitVision/frontend/src/utils/poseRecognition.ts)**
    *   **作用**: 动作识别引擎。
    *   **功能**:
        *   对关键点做横纵比校正与躯干尺度归一化，消除摄像头距离和画面比例的影响。
        *   根据肩宽/髋宽与躯干长度的比值自动判断正面或侧面视角。
        *   为深蹲、俯卧撑、开合跳提供各自的动作量测量与加权评分，并输出具体错误标签。
        *   使用带迟滞（hysteresis）、最短停留时间和最小动作幅度的状态机计数，避免抖动误计数。
        *   平板支撑单独使用稳定性历史、保持阈值与计时逻辑。
        *   关键点可见度过低时直接拒绝该帧，不参与计数与评分。

*   **[poseMatching.ts](file:///d:/code/forvue/FitVision/frontend/src/utils/poseMatching.ts)**
    *   **作用**: 共享姿态工具。
    *   **功能**: OneEuroFilter 平滑（含乱序/重复时间戳保护）与基于躯干长度的关键点归一化。

## UI 组件

项目使用了 **Element Plus** 作为 UI 组件库，并在 `components/` 下封装了自定义组件，如：
*   `PosePreview.vue`: 封装摄像头的视频流展示和骨架绘制，并展示识别置信度、视角、实时错误标签、计数与动作质量。
*   `AIRecommendations.vue`: 展示 AI 推荐的训练计划。

## 开发命令

```bash
npm run dev         # 启动开发服务器
npm run type-check  # 检查 src 与 vite 配置的 TypeScript 类型
npm run lint        # ESLint 检查
npm run test        # 运行 Vitest 单元测试
npm run build       # 类型检查 + 生产构建
```

动作识别引擎的纯函数测试位于 `src/utils/poseRecognition.test.ts`，覆盖视角判断、低可见度拒绝、深蹲深度、三种动作的计数以及平板支撑计时。

---
*文档生成时间: 2026-03-07*

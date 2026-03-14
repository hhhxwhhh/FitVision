# FitVision 项目运行指南 (Project Operation Guide)

本文档旨在指导开发人员如何在本地环境中搭建并运行 FitVision 前后端项目。

## 📋 环境准备 (Environment Preparation)

在运行 FitVision 项目之前，请按照以下步骤安装并验证必要的开发环境。

### 1. Node.js (前端运行环境)

*   **要求**: Node.js 版本需 >= 16.0 (推荐使用 LTS 版本，如 v18.x 或 v20.x)。
*   **安装**:
    *   访问 [Node.js 官网](https://nodejs.org/) 下载并安装 Windows 版本 (推荐下载 LTS 版本)。
    *   安装过程中一路点击 "Next" 即可。
*   **验证**:
    打开 PowerShell 或 CMD，运行以下命令：
    ```bash
    node -v
    # 输出示例: v18.17.0 (只要大于 v16.0.0 即可)

    npm -v
    # 输出示例: 9.6.7
    ```

### 2. Python (后端运行环境)

*   **要求**: Python 版本需 >= 3.9。
*   **安装**:
    *   访问 [Python 官网](https://www.python.org/downloads/) 下载最新的 Python 3.x 安装包。
    *   **重要**: 安装时务必勾选 **"Add Python to PATH"** (将 Python 添加到环境变量)。
*   **验证**:
    ```bash
    python --version
    # 输出示例: Python 3.11.4
    
    pip --version
    # 输出示例: pip 23.1.2 from ...
    ```

### 3. Git (版本控制工具)

*   **要求**: 任意较新版本。
*   **安装**:
    *   访问 [Git 官网](https://git-scm.com/download/win) 下载 Windows 安装程序。
    *   安装过程中推荐选择 "Git from the command line and also from 3rd-party software"。
*   **验证**:
    ```bash
    git --version
    # 输出示例: git version 2.41.0.windows.1
    ```

### 4. PostgreSQL (数据库 - 可选)

*   **说明**: 本项目默认配置为使用 SQLite (无需安装，开箱即用)，适合开发和测试。如果您希望使用 PostgreSQL：
*   **安装**:
    *   访问 [PostgreSQL 官网](https://www.postgresql.org/download/windows/) 下载并安装。
    *   记录下安装时设置的 `postgres` 超级用户密码。
*   **验证**:
    ```bash
    psql --version
    # 输出示例: psql (PostgreSQL) 15.3
    ```

## 🚀 后端启动流程 (Backend Setup)

后端基于 Django，位于 `FitVision/backend` 目录。

### 1. 进入后端目录
```bash
cd d:\code\forvue\FitVision\backend
```

### 2. 创建并激活虚拟环境 (推荐)
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
```

### 4. 配置环境变量
在 `backend` 目录下创建 `.env` 文件，并添加以下配置 (根据实际情况修改)：

```ini
# 数据库配置 (默认使用 SQLite，可跳过)
# DB_NAME=fitvision
# DB_USER=postgres
# DB_PASSWORD=your_password
# DB_HOST=localhost
# DB_PORT=5432

# VLM 视觉大模型配置 (必填，否则无法使用 AI 诊断)
CN_VLM_API_KEY=your_api_key_here
CN_VLM_MODEL=doubao-1.5-vision-pro-250328
CN_VLM_BASE_URL=https://openkey.cloud/v1

# Django 密钥 (生产环境请修改)
SECRET_KEY=django-insecure-your-secret-key
DEBUG=True
```

### 5. 数据库迁移
初始化数据库表结构。
```bash
python manage.py migrate
```

### 6. 导入初始数据 (可选)
如果项目包含预设的动作库数据，可以通过以下命令导入：
```bash
# 假设存在 fixtures 数据
python manage.py loaddata exercises/fixtures/data.json
```

### 7. 启动服务器
```bash
python manage.py runserver
```
后端服务将运行在 `http://127.0.0.1:8000/`。
*   API 文档地址: `http://127.0.0.1:8000/api/docs/`

---

## 🎨 前端启动流程 (Frontend Setup)

前端基于 Vue 3 + Vite，位于 `FitVision/frontend` 目录。

### 1. 进入前端目录
打开一个新的终端窗口：
```bash
cd d:\code\forvue\FitVision\frontend
```

### 2. 安装依赖
```bash
npm install
# 或者使用 yarn
yarn
```

### 3. 启动开发服务器
```bash
npm run dev
```
前端服务通常运行在 `http://localhost:5173/` (具体端口请查看终端输出)。

## 🔗 联调测试

1.  确保后端服务已启动并运行在 `8000` 端口。
2.  在浏览器打开前端页面 (如 `http://localhost:5173/`)。
3.  **注册/登录**: 尝试注册一个新用户并登录，验证 Auth 流程。
4.  **AI 诊断**: 进入“姿态诊断”页面，确保摄像头权限已开启，尝试拍摄一张照片进行分析 (需配置有效的 VLM API Key)。
5.  **训练**: 进入“训练”页面，尝试做一个深蹲动作，观察计数器是否工作。

## ⚠️ 常见问题 (Troubleshooting)

*   **Q: 摄像头无法打开？**
    *   A: 请检查浏览器权限设置，确保允许网站访问摄像头。同时确保没有其他应用占用摄像头。
*   **Q: AI 分析报错？**
    *   A: 请检查 `.env` 文件中的 `CN_VLM_API_KEY` 是否正确配置，以及网络是否能访问 `CN_VLM_BASE_URL`。
*   **Q: 跨域错误 (CORS)？**
    *   A: 检查后端 `settings.py` 中的 `CORS_ALLOWED_ORIGINS` 配置，确保包含前端的地址 (如 `http://localhost:5173`)。

---
*文档生成时间: 2026-03-07*

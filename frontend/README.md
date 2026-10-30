# FitVision Frontend

FitVision 的 Web 客户端：Vue 3 + TypeScript + Vite + Element Plus。

完整的项目介绍、架构与部署方式见根目录 [README](../README.md)。

## 开发

```bash
npm install
cp .env.example .env
npm run dev
```

默认运行在 http://localhost:5173 ，并将 `/api`、`/media`、`/static`
代理到 `http://127.0.0.1:8000`。可通过 `VITE_DEV_PROXY_TARGET` 修改代理目标。

## 脚本

| 命令 | 说明 |
| --- | --- |
| `npm run dev` | 启动开发服务器 |
| `npm run build` | 类型检查并构建生产包到 `dist/` |
| `npm run preview` | 本地预览生产构建 |
| `npm run type-check` | `vue-tsc` 类型检查 |
| `npm run lint` / `lint:fix` | ESLint 检查 / 自动修复 |
| `npm run format` | Prettier 格式化 |

## 目录

```text
src/
├── api/          # axios 实例、令牌刷新、媒体地址解析
├── components/   # 通用组件
├── composables/  # 姿态检测、AI 诊断等组合式逻辑
├── layouts/      # 应用外壳与导航
├── router/       # 懒加载路由、鉴权守卫、标题
├── stores/       # Pinia 状态
├── views/        # 页面
└── style.css     # 全局样式与动效
public/
├── icons/        # PWA 图标
├── manifest.webmanifest
└── sw.js         # 离线应用外壳
```

## 环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `VITE_API_BASE_URL` | `/api` | 生产环境可配置为完整 API 地址 |
| `VITE_DEV_PROXY_TARGET` | `http://127.0.0.1:8000` | 开发代理目标 |

## 构建产物

生产构建由多阶段 Dockerfile 构建，并由 nginx 提供静态资源与 `/api` 反向代理，
详见 [Dockerfile](Dockerfile) 与 [nginx.conf](nginx.conf)。

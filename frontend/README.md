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

## 界面能力

- **设计系统**：全局 `--fv-*` 令牌统一颜色、圆角、阴影与动效，旧的 `--milan-*`
  变量作为兼容别名保留，老页面无需逐个改写即可跟随主题。
- **明暗主题**：浅色 / 深色 / 跟随系统三种模式，写入 `localStorage`，首屏由内联脚本
  提前应用，避免闪白。
- **命令面板**：`Ctrl/⌘ + K` 打开，可搜索动作库、跳转页面、切换主题，支持方向键与
  回车操作。
- **状态驾驶舱**：首页根据疲劳、训练量、连续天数与本周节奏生成今日状态评分和教练洞察。
- **PWA 与离线提示**：支持安装到桌面，离线时在顶栏与页脚给出明确状态。
- **数据导出**：数据中心可将每日统计导出为带 BOM 的 CSV，直接用 Excel 打开。

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

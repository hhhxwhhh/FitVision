<template>
  <div class="main-layout">
    <a href="#main-content" class="skip-link">跳到主要内容</a>

    <header class="app-header">
      <div class="header-inner container">
        <router-link to="/" class="brand">
          <span class="brand-mark">FV</span>
          <span class="brand-name">FitVision</span>
        </router-link>

        <nav class="desktop-nav" aria-label="主导航">
          <button
            v-for="item in primaryNav"
            :key="item.path"
            type="button"
            class="nav-link"
            :class="{ active: isActive(item) }"
            :aria-current="isActive(item) ? 'page' : undefined"
            @click="router.push(item.path)"
          >
            <el-icon><component :is="item.icon" /></el-icon>
            {{ item.label }}
          </button>
        </nav>

        <div class="header-actions">
          <button class="search-trigger" type="button" @click="openPalette">
            <el-icon><Search /></el-icon>
            <span class="search-label">搜索动作或页面</span>
            <kbd>⌘K</kbd>
          </button>

          <el-tooltip content="键盘快捷键" placement="bottom">
            <button class="icon-btn shortcuts-trigger" type="button" aria-label="键盘快捷键" @click="openShortcuts">
              <el-icon><QuestionFilled /></el-icon>
            </button>
          </el-tooltip>

          <el-tooltip v-if="canInstall" content="安装 FitVision 到桌面" placement="bottom">
            <button class="icon-btn" type="button" aria-label="安装应用" @click="handleInstall">
              <el-icon><Download /></el-icon>
            </button>
          </el-tooltip>

          <ThemeToggle />

          <el-dropdown trigger="click" @command="handleUserCommand">
            <button class="user-badge" type="button">
              <el-avatar :size="30" :src="userStore.userAvatar" :icon="UserFilled" />
              <span class="username">{{ userStore.userName || '我的账户' }}</span>
              <el-icon class="chevron"><ArrowDown /></el-icon>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon>个人中心
                </el-dropdown-item>
                <el-dropdown-item command="logout" divided>
                  <el-icon><SwitchButton /></el-icon>退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>

          <button class="icon-btn mobile-only" type="button" aria-label="打开菜单" @click="mobileOpen = true">
            <el-icon><Menu /></el-icon>
          </button>
        </div>
      </div>
    </header>

    <div v-if="!online" class="offline-bar">
      <el-icon><Warning /></el-icon>
      当前处于离线状态，部分功能暂不可用
    </div>

    <main id="main-content" class="app-main" tabindex="-1">
      <div class="container app-content">
        <router-view v-slot="{ Component, route: currentRoute }">
          <Transition name="fade-slide" mode="out-in">
            <component :is="Component" :key="currentRoute.path" />
          </Transition>
        </router-view>
      </div>
    </main>

    <footer class="app-footer">
      <div class="container footer-inner">
        <div class="footer-brand">
          <span class="brand-mark small">FV</span>
          <span>FitVision · Move better, every rep.</span>
        </div>
        <div class="footer-meta">
          <span class="status-dot" :class="{ offline: !online }"></span>
          {{ online ? '服务在线' : '离线模式' }}
          <span class="divider">·</span>
          © {{ year }}
        </div>
      </div>
    </footer>

    <el-drawer v-model="mobileOpen" direction="rtl" size="290px" :with-header="false" class="mobile-drawer">
      <div class="drawer-content">
        <div class="drawer-header">
          <span class="brand-mark">FV</span>
          <div>
            <strong>FitVision</strong>
            <small>AI 健身教练</small>
          </div>
        </div>

        <nav class="drawer-nav" aria-label="移动端导航">
          <template v-for="group in mobileNav" :key="group.label">
            <div class="drawer-group">{{ group.label }}</div>
            <button
              v-for="item in group.items"
              :key="item.path"
              type="button"
              class="drawer-link"
              :class="{ active: isActive(item) }"
              :aria-current="isActive(item) ? 'page' : undefined"
              @click="navigate(item.path)"
            >
              <el-icon><component :is="item.icon" /></el-icon>
              {{ item.label }}
              <el-icon class="drawer-arrow"><ArrowRight /></el-icon>
            </button>
          </template>
        </nav>

        <div class="drawer-footer">
          <ThemeToggle />
          <span>{{ userStore.userName || '健身者' }}</span>
        </div>
      </div>
    </el-drawer>

    <CommandPalette ref="paletteRef" />
    <ShortcutsDialog ref="shortcutsRef" />
    <BackToTop />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Aim,
  ArrowDown,
  ArrowRight,
  DataAnalysis,
  Download,
  HomeFilled,
  MagicStick,
  Menu,
  QuestionFilled,
  Reading,
  Search,
  SwitchButton,
  TrendCharts,
  Trophy,
  User,
  UserFilled,
  VideoCamera,
  Warning,
} from '@element-plus/icons-vue'
import { useUserStore } from '../stores/userStore'
import { useOnlineStatus } from '../composables/useOnlineStatus'
import { usePwaInstall } from '../composables/usePwaInstall'
import ThemeToggle from '../components/ThemeToggle.vue'
import CommandPalette from '../components/CommandPalette.vue'
import ShortcutsDialog from '../components/ShortcutsDialog.vue'
import BackToTop from '../components/BackToTop.vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const paletteRef = ref<InstanceType<typeof CommandPalette> | null>(null)
const shortcutsRef = ref<InstanceType<typeof ShortcutsDialog> | null>(null)
const mobileOpen = ref(false)
const year = new Date().getFullYear()

const { online } = useOnlineStatus()
const { canInstall, install } = usePwaInstall()

const primaryNav = [
  { path: '/', label: '首页', icon: HomeFilled, exact: true },
  { path: '/training', label: '训练', icon: VideoCamera, matches: ['/training', '/posture-diagnosis', '/ai-plan'] },
  { path: '/exercises', label: '动作库', icon: Reading, matches: ['/exercises'] },
  { path: '/analytics', label: '数据', icon: DataAnalysis, matches: ['/analytics'] },
  { path: '/growth', label: '成长', icon: Trophy, matches: ['/growth'] },
]

const mobileNav = [
  {
    label: '开始',
    items: [
      { path: '/', label: '首页', icon: HomeFilled, exact: true },
      { path: '/training', label: '智能训练', icon: VideoCamera, matches: ['/training'] },
      { path: '/ai-plan', label: 'AI 训练计划', icon: MagicStick, matches: ['/ai-plan'] },
      { path: '/posture-diagnosis', label: '姿态诊断', icon: Aim, matches: ['/posture-diagnosis'] },
    ],
  },
  {
    label: '探索',
    items: [
      { path: '/exercises', label: '动作百科', icon: Reading, matches: ['/exercises'] },
      { path: '/exercises/graph', label: '知识图谱', icon: TrendCharts, matches: ['/exercises/graph'] },
      { path: '/analytics', label: '数据中心', icon: DataAnalysis, matches: ['/analytics'] },
      { path: '/growth', label: '成长中心', icon: Trophy, matches: ['/growth'] },
    ],
  },
]

interface NavItem {
  path: string
  exact?: boolean
  matches?: string[]
}

const isActive = (item: NavItem) => {
  const path = route.path
  if (item.exact) return path === item.path
  if (item.matches) return item.matches.some((prefix) => path.startsWith(prefix))
  return path === item.path || path.startsWith(`${item.path}/`)
}

const openPalette = () => paletteRef.value?.open()
const openShortcuts = () => shortcutsRef.value?.open()

const navigate = (path: string) => {
  mobileOpen.value = false
  router.push(path)
}

const handleInstall = async () => {
  const accepted = await install()
  if (accepted) ElMessage.success('FitVision 已开始安装')
}

const handleUserCommand = (command: string) => {
  if (command === 'profile') {
    router.push('/profile')
    return
  }

  if (command === 'logout') {
    ElMessageBox.confirm('确定要退出登录吗？', '退出登录', {
      confirmButtonText: '退出',
      cancelButtonText: '取消',
      type: 'warning',
    }).then(() => {
      userStore.logout()
      router.push('/login')
      ElMessage.success('已安全退出')
    })
  }
}

watch(
  () => route.fullPath,
  () => {
    mobileOpen.value = false
    window.scrollTo({ top: 0 })
  },
)

onMounted(async () => {
  if (!userStore.user) await userStore.fetchUser()
})
</script>

<style scoped>
.main-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  position: sticky;
  top: 0;
  z-index: 90;
  height: var(--header-height);
  border-bottom: 1px solid var(--fv-border);
  background: color-mix(in srgb, var(--fv-bg) 78%, transparent);
  backdrop-filter: blur(18px) saturate(160%);
  -webkit-backdrop-filter: blur(18px) saturate(160%);
}

.header-inner {
  height: 100%;
  display: flex;
  align-items: center;
  gap: 18px;
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: var(--fv-text);
  text-decoration: none;
  flex: none;
}

.brand-mark {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  background: var(--fv-gradient);
  color: #fff;
  font-size: 13px;
  font-weight: 900;
  letter-spacing: -0.04em;
  box-shadow: var(--fv-shadow-glow);
}

.brand-mark.small {
  width: 28px;
  height: 28px;
  border-radius: 9px;
  font-size: 10px;
  box-shadow: none;
}

.brand-name {
  font-size: 18px;
  font-weight: 850;
  letter-spacing: -0.035em;
}

.desktop-nav {
  display: flex;
  align-items: center;
  gap: 2px;
  flex: 1;
  justify-content: center;
}

.nav-link {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 9px 14px;
  border: none;
  border-radius: 11px;
  background: transparent;
  color: var(--fv-text-2);
  font-family: inherit;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition:
    color 0.2s ease,
    background 0.2s ease;
}

.nav-link:hover {
  color: var(--fv-text);
  background: var(--fv-surface-2);
}

.nav-link.active {
  color: var(--fv-primary);
  background: var(--fv-primary-soft);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: none;
}

.search-trigger {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 38px;
  padding: 0 10px 0 12px;
  border: 1px solid var(--fv-border);
  border-radius: 11px;
  background: var(--fv-surface);
  color: var(--fv-text-2);
  font-family: inherit;
  font-size: 13px;
  cursor: pointer;
  transition:
    border-color 0.2s ease,
    color 0.2s ease;
}

.search-trigger:hover {
  border-color: var(--fv-primary);
  color: var(--fv-primary);
}

.search-trigger kbd {
  padding: 2px 6px;
  border-radius: 5px;
  border: 1px solid var(--fv-border);
  background: var(--fv-surface-2);
  color: var(--fv-text-3);
  font-family: inherit;
  font-size: 10.5px;
}

.icon-btn {
  width: 38px;
  height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--fv-border);
  border-radius: 12px;
  background: var(--fv-surface);
  color: var(--fv-text-2);
  cursor: pointer;
  transition:
    color 0.2s ease,
    background 0.2s ease;
}

.icon-btn:hover {
  color: var(--fv-primary);
  background: var(--fv-primary-soft);
}

.user-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 38px;
  padding: 0 8px 0 4px;
  border: 1px solid var(--fv-border);
  border-radius: 999px;
  background: var(--fv-surface);
  color: var(--fv-text);
  font-family: inherit;
  cursor: pointer;
  transition: background 0.2s ease;
}

.user-badge:hover {
  background: var(--fv-surface-2);
}

.username {
  max-width: 110px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13.5px;
  font-weight: 600;
}

.chevron {
  color: var(--fv-text-3);
  font-size: 12px;
  margin-right: 4px;
}

.mobile-only {
  display: none;
}

.offline-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 8px 16px;
  font-size: 12.5px;
  font-weight: 600;
  color: #92400e;
  background: #fef3c7;
  border-bottom: 1px solid #fde68a;
}

:global(html.dark) .offline-bar {
  color: #fcd34d;
  background: rgba(120, 53, 15, 0.35);
  border-color: rgba(245, 158, 11, 0.3);
}

.app-main {
  flex: 1;
  min-width: 0;
}

.app-content {
  padding-top: 28px;
  padding-bottom: 56px;
}

.app-footer {
  border-top: 1px solid var(--fv-border);
  background: var(--fv-surface-translucent);
  backdrop-filter: blur(10px);
}

.footer-inner {
  min-height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  font-size: 12px;
  color: var(--fv-text-2);
}

.footer-brand,
.footer-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.footer-meta {
  gap: 6px;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--fv-success);
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.15);
}

.status-dot.offline {
  background: var(--fv-warning);
  box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.15);
}

.divider {
  color: var(--fv-text-3);
  margin: 0 2px;
}

.mobile-drawer :deep(.el-drawer__body) {
  padding: 0;
  background: var(--fv-bg);
}

.drawer-content {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  padding: 22px 18px;
}

.drawer-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 6px 22px;
  border-bottom: 1px solid var(--fv-border);
}

.drawer-header strong {
  display: block;
  font-size: 16px;
  color: var(--fv-text);
}

.drawer-header small {
  font-size: 11.5px;
  color: var(--fv-text-2);
}

.drawer-nav {
  flex: 1;
  padding-top: 14px;
}

.drawer-group {
  padding: 14px 10px 6px;
  font-size: 10.5px;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--fv-text-3);
}

.drawer-link {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 11px 12px;
  border: none;
  border-radius: 11px;
  background: transparent;
  color: var(--fv-text-2);
  font-family: inherit;
  font-size: 14px;
  font-weight: 600;
  text-align: left;
  cursor: pointer;
}

.drawer-link.active,
.drawer-link:hover {
  color: var(--fv-primary);
  background: var(--fv-primary-soft);
}

.drawer-arrow {
  margin-left: auto;
  font-size: 12px;
  opacity: 0.5;
}

.drawer-footer {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-top: 18px;
  border-top: 1px solid var(--fv-border);
  font-size: 13px;
  color: var(--fv-text-2);
}

@media (max-width: 1080px) {
  .search-label {
    display: none;
  }

  .search-trigger kbd {
    display: none;
  }
}

@media (max-width: 900px) {
  .shortcuts-trigger {
    display: none;
  }
}

@media (max-width: 900px) {
  .desktop-nav {
    display: none;
  }

  .mobile-only {
    display: inline-flex;
  }

  .header-inner {
    justify-content: space-between;
  }

  .username,
  .chevron {
    display: none;
  }

  .user-badge {
    padding: 0 4px;
    border: none;
    background: transparent;
  }
}

@media (max-width: 620px) {
  .app-content {
    padding-top: 18px;
  }

  .brand-name {
    display: none;
  }

  .footer-inner {
    flex-direction: column;
    justify-content: center;
    gap: 6px;
    padding: 14px 0;
  }
}
</style>

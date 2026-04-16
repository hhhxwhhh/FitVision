<template>
    <div class="main-layout">
        <el-container class="layout-container">
            <!--
              顶部导航栏：
              1) 左侧品牌 Logo（点击回首页）
              2) 中间主导航菜单（由路由路径驱动激活态）
              3) 右侧用户下拉菜单（个人中心 / 退出登录）
            -->
            <el-header class="header">
                <div class="header-inner container">
                    <!-- 品牌区：固定回首页入口，保证用户随时可回到主面板 -->
                    <div class="logo-section" @click="router.push('/')">
                        <div class="logo-icon">⚡</div>
                        <h1 class="logo-text">FitVision</h1>
                    </div>

                    <!--
                      主导航区：
                      使用与“用户区”一致的 el-dropdown 形式做导航分组。
                      目标：减少顶栏入口数量，同时保留功能可达性。
                    -->
                    <div class="nav-section">
                        <div class="nav-links">
                            <button class="nav-link" :class="{ active: activeMenu === 'home' }" @click="router.push('/')">
                                首页
                            </button>

                            <el-dropdown @command="handleTrainingCommand" trigger="click">
                                <button class="nav-link nav-dropdown-trigger"
                                    :class="{ active: activeMenu === 'training-group' }">
                                    训练中心
                                    <el-icon class="el-icon--right"><arrow-down /></el-icon>
                                </button>
                                <template #dropdown>
                                    <el-dropdown-menu>
                                        <el-dropdown-item command="training">智能训练</el-dropdown-item>
                                        <el-dropdown-item command="posture-diagnosis">姿态诊断</el-dropdown-item>
                                        <el-dropdown-item command="ai-plan">AI 计划</el-dropdown-item>
                                    </el-dropdown-menu>
                                </template>
                            </el-dropdown>

                            <el-dropdown @command="handleKnowledgeCommand" trigger="click">
                                <button class="nav-link nav-dropdown-trigger"
                                    :class="{ active: activeMenu === 'knowledge-group' }">
                                    动作学习
                                    <el-icon class="el-icon--right"><arrow-down /></el-icon>
                                </button>
                                <template #dropdown>
                                    <el-dropdown-menu>
                                        <el-dropdown-item command="exercises">动作百科</el-dropdown-item>
                                        <el-dropdown-item command="exercise-graph">知识图谱</el-dropdown-item>
                                    </el-dropdown-menu>
                                </template>
                            </el-dropdown>

                            <button class="nav-link" :class="{ active: activeMenu === 'analytics' }"
                                @click="router.push('/analytics')">
                                数据中心
                            </button>
                        </div>
                    </div>

                    <!-- 用户区：展示头像和昵称，承载账户相关操作 -->
                    <div class="user-section">
                        <el-dropdown @command="handleUserCommand" trigger="click">
                            <div class="user-profile-badge">
                                <el-avatar :size="32" :src="userStore.userAvatar" :icon="UserFilled"
                                    class="user-avatar" />
                                <span class="username">{{ userStore.userName }}</span>
                                <el-icon class="el-icon--right">
                                    <arrow-down />
                                </el-icon>
                            </div>
                            <template #dropdown>
                                <el-dropdown-menu class="user-dropdown">
                                    <el-dropdown-item command="profile">
                                        <el-icon>
                                            <User />
                                        </el-icon>
                                        个人中心
                                    </el-dropdown-item>
                                    <el-dropdown-item command="logout" divided>
                                        <el-icon>
                                            <SwitchButton />
                                        </el-icon>
                                        退出登录
                                    </el-dropdown-item>
                                </el-dropdown-menu>
                            </template>
                        </el-dropdown>
                    </div>
                </div>
            </el-header>

                        <!--
                            内容区域：
                            - 通过 router-view 动态渲染当前路由对应页面
                            - 使用 route.path 作为 key，确保同路径切换时组件状态可预期
                        -->
            <el-main class="main-content">
                <div class="content-wrapper container">
                    <!-- Router View with Component Caching Strategy -->
                    <router-view v-slot="{ Component, route }">
                        <component :is="Component" :key="route.path" />
                    </router-view>
                </div>
            </el-main>
            
            <!-- 页脚：统一版权信息 -->
            <el-footer class="footer">
                <div class="footer-inner container">
                     <p>© 2024 FitVision inc. All rights reserved.</p>
                </div>
            </el-footer>

        </el-container>
    </div>
</template>

<script setup lang="ts">
// Vue 组合式 API：
// ref/watch/onMounted 用于状态与生命周期控制
import { ref, watch, computed, onMounted } from 'vue'
// 路由实例：用于页面跳转和读取当前路径
import { useRouter, useRoute } from 'vue-router'
// 头像与下拉菜单图标
import { UserFilled, User, SwitchButton, ArrowDown } from '@element-plus/icons-vue'
// 全局消息与确认弹窗
import { ElMessageBox, ElMessage } from 'element-plus'
// Pinia 用户状态仓库
import { useUserStore } from '../stores/userStore'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

// 当前激活菜单项（对应 el-menu 的 index）
const activeMenu = ref('home')

onMounted(async () => {
    // 首次加载或刷新时，若 Store 没有用户信息则主动拉取。
    // 目的：避免刷新后导航栏昵称和头像丢失。
    if (!userStore.user) {
        await userStore.fetchUser()
    }
})

watch(() => route.path, (path) => {
    // 将“路由路径”映射为“菜单索引”，控制顶部导航高亮。
    // 这里使用 startsWith 兼容子路由，例如 /training/report 仍高亮训练菜单。
    if (path === '/') activeMenu.value = 'home'
    else if (path.startsWith('/training') || path.startsWith('/ai-plan') || path === '/posture-diagnosis') activeMenu.value = 'training-group'
    else if (path === '/exercises/graph' || path.startsWith('/exercises')) activeMenu.value = 'knowledge-group'
    else if (path.startsWith('/analytics')) activeMenu.value = 'analytics'
    else if (path.startsWith('/profile')) activeMenu.value = 'profile'
}, { immediate: true })

const handleTrainingCommand = (command: string) => {
    switch (command) {
        case 'training':
            router.push('/training')
            break
        case 'posture-diagnosis':
            router.push('/posture-diagnosis')
            break
        case 'ai-plan':
            router.push('/ai-plan')
            break
    }
}

const handleKnowledgeCommand = (command: string) => {
    switch (command) {
        case 'exercises':
            router.push('/exercises')
            break
        case 'exercise-graph':
            router.push('/exercises/graph')
            break
    }
}

const handleUserCommand = (command: string) => {
    // 用户下拉菜单命令处理：
    // - logout：二次确认后清理登录状态并跳转登录页
    // - profile：进入个人中心
    if (command === 'logout') {
        ElMessageBox.confirm('确定要退出登录吗？', '确认', {
            confirmButtonText: '退出',
            cancelButtonText: '取消',
            type: 'warning'
        }).then(() => {
            userStore.logout()
            router.push('/login')
            ElMessage.success('已安全退出')
        })
    } else if (command === 'profile') {
        router.push('/profile')
    }
}
</script>

<style scoped>
/* 页面级容器：撑满视口，保证页脚在底部 */
.layout-container {
    min-height: 100vh;
    --milan-page-bg: #EEE6DB;
    --milan-page-bg-soft: #E4D8C8;
    --milan-surface: #FBF8F3;
    --milan-surface-2: #F5F0E8;
    --milan-border: #E5E0D8;
    --milan-text-primary: #3C2F2F;
    --milan-text-secondary: #7D756D;
    --milan-accent: #BEA47E;
    --milan-accent-deep: #9F8462;

    background:
        radial-gradient(900px 280px at 8% -10%, rgba(245, 242, 237, 0.68), transparent 60%),
        radial-gradient(980px 320px at 100% 0%, rgba(213, 198, 176, 0.28), transparent 62%),
        linear-gradient(180deg, var(--milan-page-bg) 0%, var(--milan-page-bg-soft) 100%);
}

/* 顶栏：吸顶 + 轻阴影，保持导航可见性 */
.header {
    height: var(--header-height) !important;
    background: linear-gradient(180deg, #FEFCF8 0%, #FBF7F1 100%);
    border-bottom: 1px solid #ECE4D8;
    position: sticky;
    top: 0;
    z-index: 100;
    padding: 0;
    box-shadow: 0 4px 14px rgba(60, 47, 47, 0.05);
}

/* 顶栏内部三段布局：左 Logo / 中菜单 / 右用户区 */
.header-inner {
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

/* Logo 样式：图标与标题作为品牌识别点 */
.logo-section {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    user-select: none;
}

.logo-icon {
    font-size: 24px;
    background: linear-gradient(135deg, #BEA47E 0%, #9F8462 100%);
    background-clip: text;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    /* Emoji fallback */
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 8px;
    background: #EFE8DD;
    color: #9F8462;
    -webkit-text-fill-color: initial;
}

.logo-text {
    font-size: 20px;
    font-weight: 800;
    color: var(--milan-text-primary);
    margin: 0;
    letter-spacing: -0.5px;
}

/* 导航区域：居中显示收敛后的主入口 */
.nav-section {
    flex: 1;
    display: flex;
    justify-content: center;
}

.nav-links {
    display: flex;
    align-items: center;
    gap: 8px;
}

.nav-link {
    border: none;
    background: transparent;
    cursor: pointer;
    padding: 10px 12px;
    border-radius: 10px;
    font-size: 15px;
    font-weight: 500;
    color: var(--milan-text-secondary);
    display: inline-flex;
    align-items: center;
    gap: 4px;
    transition: all 0.2s ease;
}

.nav-link.active {
    color: var(--milan-accent-deep);
    font-weight: 600;
    background: #EFE8DD;
}

.nav-link:hover {
    color: var(--milan-text-primary);
    background: var(--milan-surface-2);
}

.nav-dropdown-trigger :deep(.el-icon) {
    font-size: 14px;
}

/* 用户资料入口：小胶囊形态，符合账户操作区特征 */
.user-profile-badge {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 12px;
    border-radius: 20px;
    cursor: pointer;
    transition: background 0.2s;
}

.user-profile-badge:hover {
    background-color: var(--milan-surface-2);
}

.username {
    font-size: 14px;
    font-weight: 500;
    color: var(--milan-text-primary);
}

.user-avatar {
    background: var(--milan-accent);
    color: #F5F2ED;
}

/* 主内容区：横向不溢出，避免图表类组件撑破布局 */
.main-content {
    padding: 0;
    flex: 1;
    overflow-x: hidden;
}

/* 内容上下留白：给页面卡片和标题提供呼吸感 */
.content-wrapper {
    padding-top: 32px;
    padding-bottom: 48px;
}

/* 页脚：弱化视觉权重，作为收尾信息区 */
.footer {
    background: color-mix(in srgb, var(--milan-surface) 90%, white 10%);
    border-top: 1px solid var(--milan-border);
    padding: 0;
    height: auto;
}

.footer-inner {
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--milan-text-secondary);
    font-size: 13px;
}

.main-layout :deep(.el-dropdown-menu) {
    background: var(--milan-surface);
    border: 1px solid var(--milan-border);
    box-shadow: 0 8px 18px rgba(60, 47, 47, 0.1);
}

.main-layout :deep(.el-dropdown-menu__item) {
    color: var(--milan-text-primary);
}

.main-layout :deep(.el-dropdown-menu__item:not(.is-disabled):hover) {
    background: var(--milan-surface-2);
    color: var(--milan-accent-deep);
}
</style>

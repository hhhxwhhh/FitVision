<template>
    <div class="main-layout">
        <el-container class="layout-container">
            <!-- 顶部导航栏 -->
            <el-header class="header">
                <div class="header-inner container">
                    <div class="logo-section" @click="router.push('/')">
                        <div class="logo-icon">⚡</div>
                        <h1 class="logo-text">FitVision</h1>
                    </div>

                    <div class="nav-section">
                        <el-menu :default-active="activeMenu" mode="horizontal" @select="handleMenuSelect"
                            :ellipsis="false" class="main-menu">
                            <el-menu-item index="home">首页</el-menu-item>
                            <el-menu-item index="training">智能训练</el-menu-item>
                            <el-menu-item index="ai-plan">AI 计划</el-menu-item>
                            <el-menu-item index="exercises">动作百科</el-menu-item>
                            <el-menu-item index="exercise-graph">知识图谱</el-menu-item>
                            <el-menu-item index="analytics">数据中心</el-menu-item>
                        </el-menu>
                    </div>

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

            <!-- 内容区域 -->
            <el-main class="main-content">
                <div class="content-wrapper container">
                    <!-- Router View with Component Caching Strategy -->
                    <router-view v-slot="{ Component, route }">
                        <component :is="Component" :key="route.path" />
                    </router-view>
                </div>
            </el-main>
            
            <el-footer class="footer">
                <div class="footer-inner container">
                     <p>© 2024 FitVision inc. All rights reserved.</p>
                </div>
            </el-footer>

        </el-container>
    </div>
</template>

<script setup lang="ts">
import { ref, watch, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { UserFilled, User, SwitchButton, ArrowDown } from '@element-plus/icons-vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/userStore'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const activeMenu = ref('home')

onMounted(async () => {
    // 首次加载或刷新，尝试拉取用户信息
    if (!userStore.user) {
        await userStore.fetchUser()
    }
})

watch(() => route.path, (path) => {
    if (path === '/') activeMenu.value = 'home'
    else if (path.startsWith('/training')) activeMenu.value = 'training'
    else if (path.startsWith('/ai-plan')) activeMenu.value = 'ai-plan'
    else if (path === '/exercises/graph') activeMenu.value = 'exercise-graph'
    else if (path.startsWith('/exercises')) activeMenu.value = 'exercises'
    else if (path.startsWith('/analytics')) activeMenu.value = 'analytics'
    else if (path.startsWith('/profile')) activeMenu.value = 'profile'
}, { immediate: true })

const handleMenuSelect = (index: string) => {
    switch (index) {
        case 'home': router.push('/'); break
        case 'training': router.push('/training'); break
        case 'ai-plan': router.push('/ai-plan'); break
        case 'exercises': router.push('/exercises'); break
        case 'exercise-graph': router.push('/exercises/graph'); break
        case 'analytics': router.push('/analytics'); break
        case 'profile': router.push('/profile'); break
    }
}

const handleUserCommand = (command: string) => {
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
.layout-container {
    min-height: 100vh;
    background-color: var(--bg-color);
}

.header {
    height: var(--header-height) !important;
    background: #ffffff;
    border-bottom: 1px solid #e2e8f0;
    position: sticky;
    top: 0;
    z-index: 100;
    padding: 0;
    box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
}

.header-inner {
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

/* Logo Styling */
.logo-section {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    user-select: none;
}

.logo-icon {
    font-size: 24px;
    background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    /* Emoji fallback */
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 8px;
    background: #e0e7ff;
    color: #4f46e5;
    -webkit-text-fill-color: initial;
}

.logo-text {
    font-size: 20px;
    font-weight: 800;
    color: #1e293b;
    margin: 0;
    letter-spacing: -0.5px;
}

/* Nav Menu Styling over Element Plus */
.nav-section {
    flex: 1;
    display: flex;
    justify-content: center;
}

.main-menu {
    border-bottom: none !important;
    background: transparent !important;
}

:deep(.el-menu-item) {
    font-size: 15px;
    font-weight: 500;
    color: #64748b !important; /* Text Secondary */
    background: transparent !important;
    height: var(--header-height);
    line-height: var(--header-height);
}

:deep(.el-menu-item.is-active) {
    color: #4f46e5 !important; /* Primary Dark */
    font-weight: 600;
    border-bottom: 2px solid #4f46e5 !important;
}

:deep(.el-menu-item:hover) {
    color: #1e293b !important;
    background: transparent !important;
}

/* User Profile */
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
    background-color: #f1f5f9;
}

.username {
    font-size: 14px;
    font-weight: 500;
    color: #334155;
}

.user-avatar {
    background: #6366f1;
    color: white;
}

/* Main Content */
.main-content {
    padding: 0;
    flex: 1;
    overflow-x: hidden;
}

.content-wrapper {
    padding-top: 32px;
    padding-bottom: 48px;
}

/* Footer */
.footer {
    background: #fff;
    border-top: 1px solid #e2e8f0;
    padding: 0;
    height: auto;
}

.footer-inner {
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #94a3b8;
    font-size: 13px;
}
</style>

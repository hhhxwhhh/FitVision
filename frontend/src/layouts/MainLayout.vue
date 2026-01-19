<template>
    <div class="main-layout">
        <el-container>
            <!-- 顶部导航栏 -->
            <el-header class="header">
                <div class="header-content">
                    <div class="logo-section" @click="router.push('/')" style="cursor: pointer;">
                        <h1 class="logo">🏋️‍♂️ FitVision</h1>
                    </div>

                    <div class="nav-section">
                        <el-menu :default-active="activeMenu" mode="horizontal" @select="handleMenuSelect"
                            background-color="#545c64" text-color="#fff" active-text-color="#ffd04b" class="nav-menu">
                            <el-menu-item index="home">首页</el-menu-item>
                            <el-menu-item index="training">训练</el-menu-item>
                            <el-menu-item index="exercises">动作库</el-menu-item>
                            <el-menu-item index="analytics">进度分析</el-menu-item>
                            <el-menu-item index="profile">个人中心</el-menu-item>
                        </el-menu>
                    </div>

                    <div class="user-section">
                        <el-dropdown @command="handleUserCommand">
                            <div class="user-profile">
                                <el-avatar :icon="UserFilled" size="small" />
                                <span class="username">{{ username }}</span>
                            </div>
                            <template #dropdown>
                                <el-dropdown-menu>
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
                <router-view v-slot="{ Component }">
                    <transition name="fade" mode="out-in">
                        <component :is="Component" />
                    </transition>
                </router-view>
            </el-main>

            <el-footer class="footer">
                <div class="footer-content">
                    <p>© 2024 FitVision AI 智能健身系统 | 科技赋能运动</p>
                </div>
            </el-footer>
        </el-container>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { UserFilled, User, SwitchButton } from '@element-plus/icons-vue'
import { ElMessageBox, ElMessage } from 'element-plus'

const router = useRouter()
const route = useRoute()
const username = ref(localStorage.getItem('username') || '健身达人')
const activeMenu = ref('home')

// 根据当前路由更新激活的菜单项
watch(() => route.path, (path) => {
    if (path === '/') activeMenu.value = 'home'
    else if (path.startsWith('/training')) activeMenu.value = 'training'
    else if (path.startsWith('/exercises')) activeMenu.value = 'exercises'
    else if (path.startsWith('/analytics')) activeMenu.value = 'analytics'
    else if (path.startsWith('/profile')) activeMenu.value = 'profile'
}, { immediate: true })

const handleMenuSelect = (index: string) => {
    switch (index) {
        case 'home': router.push('/'); break
        case 'training': router.push('/training'); break
        case 'exercises': router.push('/exercises'); break
        case 'analytics': router.push('/analytics'); break
        case 'profile': router.push('/profile'); break
    }
}

const handleUserCommand = (command: string) => {
    if (command === 'logout') {
        ElMessageBox.confirm('确定要退出登录吗？', '提示', {
            type: 'warning'
        }).then(() => {
            localStorage.removeItem('jwt_token')
            localStorage.removeItem('username')
            router.push('/login')
            ElMessage.success('已安全退出')
        })
    } else if (command === 'profile') {
        router.push('/profile')
    }
}
</script>

<style scoped>
.main-layout {
    min-height: 100vh;
    background-color: #f5f7fa;
}

.header {
    background-color: #545c64;
    color: white;
    padding: 0;
    height: 60px !important;
    line-height: 60px;
    position: sticky;
    top: 0;
    z-index: 100;
}

.header-content {
    max-width: 1200px;
    margin: 0 auto;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 20px;
}

.logo-section h1 {
    margin: 0;
    font-size: 22px;
    font-weight: bold;
    color: #ffd04b;
}

.nav-menu {
    border-bottom: none;
}

.user-profile {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    color: #fff;
}

.main-content {
    max-width: 1200px;
    margin: 0 auto;
    width: 100%;
    padding: 20px;
    min-height: calc(100vh - 120px);
}

.footer {
    text-align: center;
    color: #909399;
    padding: 20px 0;
    border-top: 1px solid #e6e6e6;
    background: white;
}

.fade-enter-active,
.fade-leave-active {
    transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
    opacity: 0;
}

@media (max-width: 768px) {
    .nav-section {
        display: none;
    }
}
</style>

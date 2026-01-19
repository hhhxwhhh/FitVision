<template>
  <div class="home-layout">
    <!-- 顶部导航栏 -->
    <el-header class="header">
      <div class="header-content">
        <div class="logo-section">
          <h1 class="logo">🏋️‍♂️ FitVision</h1>
        </div>

        <div class="nav-section">
          <el-menu :default-active="activeMenu" mode="horizontal" @select="handleMenuSelect" background-color="#545c64"
            text-color="#fff" active-text-color="#ffd04b" class="nav-menu">
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
                <el-dropdown-item command="settings">
                  <el-icon>
                    <Setting />
                  </el-icon>
                  设置
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

    <!-- 主要内容区域 -->
    <el-main class="main-content">
      <!-- 欢迎横幅 -->
      <div class="welcome-banner">
        <h2>欢迎回来，{{ username }}!</h2>
        <p>今天你想进行哪种训练？</p>
      </div>

      <!-- 快捷功能区 -->
      <div class="quick-actions">
        <el-row :gutter="20">
          <el-col :xs="24" :sm="12" :md="6">
            <el-card class="action-card" @click="startSquatTraining">
              <div class="action-content">
                <div class="action-icon">🦵</div>
                <h3>深蹲训练</h3>
                <p>AI视觉识别技术</p>
              </div>
            </el-card>
          </el-col>

          <el-col :xs="24" :sm="12" :md="6">
            <el-card class="action-card" @click="viewWorkoutPlan">
              <div class="action-content">
                <div class="action-icon">📋</div>
                <h3>训练计划</h3>
                <p>定制专属方案</p>
              </div>
            </el-card>
          </el-col>

          <el-col :xs="24" :sm="12" :md="6">
            <el-card class="action-card" @click="checkProgress">
              <div class="action-content">
                <div class="action-icon">📈</div>
                <h3>进度追踪</h3>
                <p>查看健身成果</p>
              </div>
            </el-card>
          </el-col>

          <el-col :xs="24" :sm="12" :md="6">
            <el-card class="action-card" @click="viewExercises">
              <div class="action-content">
                <div class="action-icon">📖</div>
                <h3>动作百科</h3>
                <p>学习标准动作</p>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>

      <!-- 统计信息区 -->
      <div class="stats-section" v-loading="loading">
        <el-card class="stats-card">
          <template #header>
            <div class="card-header">
              <span>健身数据统计</span>
            </div>
          </template>

          <el-row :gutter="20">
            <el-col :span="6">
              <div class="stat-item">
                <div class="stat-value">{{ dashboardData.stats.trainings }}</div>
                <div class="stat-label">总训练次数</div>
              </div>
            </el-col>

            <el-col :span="6">
              <div class="stat-item">
                <div class="stat-value">{{ dashboardData.stats.calories }}</div>
                <div class="stat-label">总消耗卡路里</div>
              </div>
            </el-col>

            <el-col :span="6">
              <div class="stat-item">
                <div class="stat-value">{{ dashboardData.stats.duration }}</div>
                <div class="stat-label">总训练时长</div>
              </div>
            </el-col>

            <el-col :span="6">
              <div class="stat-item">
                <div class="stat-value">{{ dashboardData.stats.streak }}</div>
                <div class="stat-label">历史最长连胜</div>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </div>

      <!-- 最近活动和推荐 -->
      <div class="content-section">
        <el-row :gutter="20">
          <el-col :xs="24" :md="16">
            <el-card class="recent-activity" v-loading="loading">
              <template #header>
                <div class="card-header">
                  <span>最近训练记录</span>
                </div>
              </template>

              <el-table :data="dashboardData.recentActivities" style="width: 100%">
                <el-table-column prop="date" label="日期" />
                <el-table-column prop="type" label="类型" />
                <el-table-column prop="duration" label="时长" />
                <el-table-column prop="calories" label="消耗(卡)" />
                <el-table-column label="评分">
                  <template #default="scope">
                    <el-tag :type="scope.row.score > 80 ? 'success' : 'warning'">{{ scope.row.score || '-' }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="操作">
                  <template #default="scope">
                    <el-button size="small" @click="viewDetail(scope.row)">详情</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-card>
          </el-col>

          <el-col :xs="24" :md="8">
            <el-card class="recommendations">
              <template #header>
                <div class="card-header">
                  <span>AI 推荐</span>
                </div>
              </template>

              <div class="recommendation-list">
                <div class="recommendation-item" v-for="item in recommendations" :key="item.id">
                  <h4>{{ item.title }}</h4>
                  <p>{{ item.description }}</p>
                  <el-button type="primary" size="small" @click="followRecommendation(item)">
                    {{ item.action }}
                  </el-button>
                </div>
              </div>
            </el-card>

            <el-card class="daily-tip" style="margin-top: 20px;">
              <template #header>
                <div class="card-header">
                  <span>每日贴士</span>
                </div>
              </template>

              <div class="tip-content">
                <p>💪 今日建议：训练前进行充分热身，每个动作保持标准姿势比追求次数更重要。</p>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </el-main>

    <!-- 底部信息栏 -->
    <el-footer class="footer">
      <div class="footer-content">
        <p>© 2025 FitVision 智能健身 - 你的AI私人健身教练</p>
        <div class="footer-links">
          <el-link type="info" @click="showAbout">关于我们</el-link>
          <el-link type="info" @click="showPrivacy">隐私政策</el-link>
          <el-link type="info" @click="showTerms">服务条款</el-link>
        </div>
      </div>
    </el-footer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import {
  UserFilled,
  User,
  Setting,
  SwitchButton
} from '@element-plus/icons-vue'
import {
  ElMessage,
  ElMessageBox,
  ElNotification
} from 'element-plus'
import apiClient from '../api'

const router = useRouter()
const username = ref(localStorage.getItem('username') || '用户')
const activeMenu = ref('home')
const loading = ref(false)

// 仪表盘数据
const dashboardData = reactive({
  stats: {
    trainings: 0,
    calories: 0,
    duration: '0分钟',
    streak: 0
  },
  recentActivities: [] as any[],
  activeGoals: [] as any[]
})

// 获取仪表盘数据
const fetchDashboardData = async () => {
  loading.value = true
  try {
    const res = await apiClient.get('auth/dashboard/')
    const data = res.data

    // 映射后端数据 (对应 backend/users/views.py 中的 user_dashboard)
    dashboardData.stats = {
      trainings: data.stats.total_trainings,
      calories: Math.round(data.stats.total_calories_burned),
      duration: `${data.stats.total_training_time}分钟`,
      streak: data.stats.longest_training_streak || 0
    }

    dashboardData.recentActivities = data.recent_logs.map((log: any) => ({
      id: log.id,
      date: new Date(log.created_at).toLocaleDateString(),
      type: log.action_name,
      duration: `${Math.floor(log.duration / 60)}分钟`,
      calories: log.calories,
      score: log.accuracy_score
    }))

    dashboardData.activeGoals = data.active_goals
  } catch (err: any) {
    console.error('获取仪表盘数据失败', err)
    ElMessage.error('无法同步最新的健身数据')
  } finally {
    loading.value = false
  }
}

// AI推荐内容
const recommendations = ref([
  {
    id: 1,
    title: '增加训练强度',
    description: '根据你的表现，建议增加深蹲组数至4组',
    action: '查看详情'
  },
  {
    id: 2,
    title: '恢复日提醒',
    description: '连续训练3天，明天安排休息或轻度活动',
    action: '调整计划'
  }
])

onMounted(() => {
  fetchDashboardData()
  // 显示欢迎通知
  ElNotification({
    title: '欢迎回来',
    message: `你好，${username.value}！今天也要坚持锻炼哦！`,
    type: 'success',
    duration: 3000
  })
})

// 菜单选择处理
const handleMenuSelect = (index: string) => {
  activeMenu.value = index
  switch (index) {
    case 'home':
      router.push('/')
      break
    case 'training':
      router.push('/training')
      break
    case 'exercises':
      router.push('/exercises')
      break
    case 'analytics':
      router.push('/analytics')
      break
    case 'profile':
      router.push('/profile')
      break
  }
}

// 用户命令处理
const handleUserCommand = (command: string) => {
  switch (command) {
    case 'profile':
      router.push('/profile')
      break
    case 'settings':
      router.push('/settings')
      break
    case 'logout':
      handleLogout()
      break
  }
}

// 退出登录
const handleLogout = () => {
  ElMessageBox.confirm(
    '确定要退出登录吗？',
    '确认退出',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    }
  ).then(() => {
    // 清除本地存储的认证信息
    localStorage.removeItem('jwt_token')
    localStorage.removeItem('username')

    // 跳转到登录页
    ElMessage.success('已退出登录')
    router.push('/login')
  }).catch(() => {
    // 用户取消操作
  })
}

// 功能按钮处理
const startSquatTraining = () => {
  ElMessage.info('即将进入深蹲训练模式')
  router.push('/training')
}

const viewWorkoutPlan = () => {
  ElMessage.info('查看训练计划')
  // TODO: 实现跳转到训练计划页面
}

const checkProgress = () => {
  ElMessage.info('查看进度追踪')
  // TODO: 实现跳转到进度页面
}

const viewExercises = () => {
  ElMessage.info('浏览动作百科')
  // TODO: 实现跳转到动作库页面
}

const viewDetail = (row: any) => {
  ElMessage.info(`查看 ${row.type} 的详细记录`)
  // TODO: 实现查看详情功能
}

const followRecommendation = (item: any) => {
  ElMessage.info(`处理推荐项: ${item.title}`)
  // TODO: 实现处理推荐项功能
}

// 底部链接处理
const showAbout = () => {
  ElMessage.info('显示关于我们信息')
  // TODO: 实现显示关于我们的信息
}

const showPrivacy = () => {
  ElMessage.info('显示隐私政策')
  // TODO: 实现显示隐私政策
}

const showTerms = () => {
  ElMessage.info('显示服务条款')
  // TODO: 实现显示服务条款
}
</script>

<style scoped>
.home-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* 头部样式 */
.header {
  background-color: #545c64;
  color: white;
  padding: 0;
  box-shadow: 0 2px 4px rgba(0, 0, 0, .1);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 100%;
  padding: 0 20px;
}

.logo-section .logo {
  margin: 0;
  font-size: 1.8rem;
  font-weight: bold;
  color: white;
}

.nav-section {
  flex: 1;
  margin: 0 20px;
}

.nav-menu {
  border: none !important;
  background-color: transparent !important;
}

.user-section .user-profile {
  display: flex;
  align-items: center;
  cursor: pointer;
  gap: 10px;
}

.username {
  font-weight: 500;
}

/* 主要内容样式 */
.main-content {
  flex: 1;
  background-color: #f5f5f5;
  padding: 20px;
}

.welcome-banner {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 10px;
  padding: 30px;
  color: white;
  margin-bottom: 30px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, .1);
}

.welcome-banner h2 {
  margin: 0 0 10px 0;
  font-size: 2rem;
}

.welcome-banner p {
  margin: 0;
  font-size: 1.1rem;
  opacity: 0.9;
}

.quick-actions {
  margin-bottom: 30px;
}

.action-card {
  cursor: pointer;
  transition: all 0.3s ease;
  height: 150px;
}

.action-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 20px rgba(0, 0, 0, .15);
}

.action-content {
  text-align: center;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

.action-icon {
  font-size: 2rem;
  margin-bottom: 10px;
}

.action-card h3 {
  margin: 10px 0 5px 0;
  font-size: 1.2rem;
}

.action-card p {
  margin: 0;
  color: #666;
  font-size: 0.9rem;
}

.stats-section {
  margin-bottom: 30px;
}

.card-header {
  font-weight: bold;
  font-size: 1.1rem;
}

.stat-item {
  text-align: center;
  padding: 15px 0;
}

.stat-value {
  font-size: 1.8rem;
  font-weight: bold;
  color: #409eff;
  margin-bottom: 5px;
}

.stat-label {
  color: #666;
  font-size: 0.9rem;
}

.content-section {
  margin-bottom: 30px;
}

.recommendation-item {
  padding: 15px 0;
  border-bottom: 1px solid #eee;
}

.recommendation-item:last-child {
  border-bottom: none;
}

.recommendation-item h4 {
  margin: 0 0 5px 0;
  font-size: 1rem;
}

.recommendation-item p {
  margin: 5px 0;
  color: #666;
  font-size: 0.9rem;
}

.tip-content p {
  margin: 0;
  line-height: 1.6;
}

/* 底部样式 */
.footer {
  background-color: #333;
  color: #fff;
  padding: 20px;
  text-align: center;
}

.footer-content {
  max-width: 1200px;
  margin: 0 auto;
}

.footer-links {
  margin-top: 10px;
}

.footer-links .el-link {
  margin: 0 10px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
    padding: 10px;
    gap: 10px;
  }

  .nav-section {
    width: 100%;
    margin: 0;
  }

  .nav-menu {
    overflow-x: auto;
  }

  .welcome-banner {
    padding: 20px;
  }

  .welcome-banner h2 {
    font-size: 1.5rem;
  }

  .stat-item {
    padding: 10px 0;
  }

  .stat-value {
    font-size: 1.4rem;
  }
}
</style>
<template>
  <div class="home-container">
    <div class="header">
      <h1>🏋️‍♂️ FitVision 智能健身</h1>
      <div class="user-info">
        <span>欢迎你，{{ username }}</span>
        <el-dropdown @command="handleUserCommand">
          <el-avatar icon="UserFilled" size="small" class="avatar" />
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">👤 个人档案</el-dropdown-item>
              <el-dropdown-item command="logout" divided>🚪 退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <div class="menu-grid">
      <el-card class="menu-item" shadow="hover" @click="$router.push('/profile')">
        <div class="menu-icon">👤</div>
        <h3>完善档案</h3>
        <p>设置身高体重，让 AI 更懂你</p>
      </el-card>

      <el-card class="menu-item highlight" shadow="hover" @click="startTraining">
        <div class="menu-icon">🚀</div>
        <h3>开始训练</h3>
        <p>AI 视觉识别深蹲</p>
        <el-tag type="warning" size="small" class="status-tag">开发中</el-tag>
      </el-card>

      <el-card class="menu-item" shadow="hover" @click="viewHistory">
        <div class="menu-icon">📊</div>
        <h3>训练记录</h3>
        <p>查看历史成就</p>
        <el-tag type="info" size="small" class="status-tag">待开发</el-tag>
      </el-card>

      <el-card class="menu-item" shadow="hover" @click="viewProgress">
        <div class="menu-icon">📈</div>
        <h3>进度追踪</h3>
        <p>查看健身成果变化</p>
        <el-tag type="info" size="small" class="status-tag">待开发</el-tag>
      </el-card>
    </div>

    <div class="stats-section">
      <el-card class="stat-card">
        <div class="stat-value">{{ stats.totalTrainings }}</div>
        <div class="stat-label">总训练次数</div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-value">{{ stats.totalCalories }}</div>
        <div class="stat-label">累计消耗(卡)</div>
      </el-card>
      <el-card class="stat-card">
        <div class="stat-value">{{ stats.currentStreak }}</div>
        <div class="stat-label">连续打卡(天)</div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const username = ref(localStorage.getItem('username') || '用户')

const stats = ref({
  totalTrainings: 0,
  totalCalories: 0,
  currentStreak: 0
})

onMounted(() => {
  loadStats()
})

const loadStats = () => {
  stats.value = {
    totalTrainings: Math.floor(Math.random() * 50),
    totalCalories: Math.floor(Math.random() * 5000),
    currentStreak: Math.floor(Math.random() * 10)
  }
}

const handleUserCommand = (command: string) => {
  switch (command) {
    case 'profile':
      router.push('/profile')
      break
    case 'logout':
      logout()
      break
  }
}

const logout = () => {
  ElMessageBox.confirm('确定要退出登录吗？', '确认退出', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    localStorage.removeItem('jwt_token')
    localStorage.removeItem('username')
    ElMessage.success('已退出登录')
    router.push('/login')
  }).catch(() => {
    // 用户取消操作
  })
}

const startTraining = () => {
  ElMessage.info('训练功能正在开发中...')
}

const viewHistory = () => {
  ElMessage.info('训练记录功能正在开发中...')
}

const viewProgress = () => {
  ElMessage.info('进度追踪功能正在开发中...')
}
</script>

<style scoped>
.home-container {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
  color: #333;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 40px;
  padding: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 10px;
  color: white;
}

.header h1 {
  margin: 0;
  font-size: 2rem;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 15px;
}

.avatar {
  cursor: pointer;
  background-color: #409eff;
}

.menu-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin-bottom: 40px;
}

.menu-item {
  cursor: pointer;
  text-align: center;
  transition: all 0.3s ease;
  position: relative;
  padding: 20px;
}

.menu-item:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
}

.menu-icon {
  font-size: 2rem;
  margin-bottom: 15px;
}

.menu-item h3 {
  margin: 10px 0;
  font-size: 1.2rem;
}

.menu-item p {
  color: #666;
  margin-bottom: 15px;
}

.status-tag {
  position: absolute;
  top: 15px;
  right: 15px;
}

.highlight {
  border: 2px solid #409EFF;
}

.stats-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-top: 30px;
}

.stat-card {
  text-align: center;
  padding: 20px;
}

.stat-value {
  font-size: 2rem;
  font-weight: bold;
  color: #409EFF;
  margin-bottom: 10px;
}

.stat-label {
  color: #666;
  font-size: 0.9rem;
}

@media (max-width: 768px) {
  .header {
    flex-direction: column;
    gap: 15px;
    text-align: center;
  }

  .menu-grid {
    grid-template-columns: 1fr;
  }

  .stats-section {
    grid-template-columns: 1fr;
  }
}
</style>
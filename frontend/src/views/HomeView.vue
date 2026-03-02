<template>
  <div class="dashboard-container">
    <div class="welcome-banner">
      <div class="banner-content">
        <h1>欢迎回来，{{ username }}! 👋</h1>
        <p>设定目标，坚持运动，AI 助你遇见更好的自己。</p>
        <div class="banner-actions">
          <el-button type="primary" size="large" @click="router.push('/training')">立即开始系统训练</el-button>
        </div>
      </div>
    </div>

    <el-alert
      v-if="userStatus?.fatigue_level > 0.7"
      title="AI 检测到您处于疲劳状态"
      type="warning"
      description="建议今天进行低强度恢复训练。我们已为您准备了专门的放松动作。"
      show-icon
      class="mb-6"
    >
      <template #default>
        <div class="mt-2">
          <el-button type="warning" size="small" @click="scrollToRecs('auto_adjust')">查看恢复建议</el-button>
        </div>
      </template>
    </el-alert>

    <section class="section">
      <h2 class="section-title">快捷入口</h2>
      <el-row :gutter="20">
        <el-col :xs="24" :sm="12" :md="6">
          <el-card class="feature-card highlighted" @click="router.push('/posture-diagnosis')">
            <div class="card-icon">🧘</div>
            <h3>AI 姿态建模诊断</h3>
            <p>实时扫描并分析体态风险</p>
          </el-card>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6">
          <el-card class="feature-card" @click="router.push('/training')">
            <div class="card-icon">📋</div>
            <h3>完成训练计划</h3>
            <p>执行今日安排的课程课程</p>
          </el-card>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6">
          <el-card class="feature-card" @click="router.push('/exercises')">
            <div class="card-icon">📖</div>
            <h3>动作库</h3>
            <p>学习 50+ 标准健身动作</p>
          </el-card>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6">
          <el-card class="feature-card" @click="router.push('/analytics')">
            <div class="card-icon">📈</div>
            <h3>进度轨迹</h3>
            <p>查看各项身体指标趋势</p>
          </el-card>
        </el-col>
      </el-row>
    </section>

    <section class="section">
      <div class="section-header">
        <h2 class="section-title">今日状态</h2>
        <el-tag v-if="profile?.bmi" :type="getBMIType(profile.bmi)" size="small" effect="plain" class="bmi-tag">
          BMI: {{ profile.bmi.toFixed(1) }} ({{ getBMIText(profile.bmi) }})
        </el-tag>
      </div>
      <el-row :gutter="20" v-loading="loading">
        <el-col :xs="24" :sm="8">
          <el-card shadow="hover" class="status-card">
            <div class="status-header">已消耗热量</div>
            <div class="status-value">{{ stats.total_calories_burned || 0 }} <span>kcal</span></div>
            <el-progress :percentage="Math.min(100, ((stats.total_calories_burned || 0) / calorieGoal) * 100)"
              :show-text="false" :color="customColors" />
            <div class="status-footer">目标: {{ calorieGoal }} kcal (基于 TDEE)</div>
          </el-card>
        </el-col>
        <el-col :xs="24" :sm="8">
          <el-card shadow="hover" class="status-card">
            <div class="status-header">累计训练时长</div>
            <div class="status-value">{{ stats.total_duration_minutes || 0 }} <span>min</span></div>
            <el-progress :percentage="Math.min(100, ((stats.total_duration_minutes || 0) / 30) * 100)"
              :show-text="false" status="success" />
            <div class="status-footer">目标: 30 min</div>
          </el-card>
        </el-col>

        <el-col :xs="24" :sm="8">
          <el-card shadow="hover" class="status-card">
            <div class="status-header">本周部位训练负荷</div>
            
            <div class="muscle-recovery-list">
              <div v-for="muscle in volumeStatus" :key="muscle.name" class="muscle-item">
                <span class="m-name">{{ muscle.name }}</span>
                <el-progress :percentage="muscle.percentage" :stroke-width="10" :color="muscle.color" />
              </div>
            </div>
            
            <div class="status-footer">基于本周实际训练容量 (重量×次数) 统计</div>
          </el-card>
        </el-col>
        </el-row>
    </section>

    <AIRecommendations ref="recommendationsRef" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import apiClient from '../api'
import AIRecommendations from '../components/AIRecommendations.vue'

const router = useRouter()
const username = ref(localStorage.getItem('username') || '健身者')
const loading = ref(false)
const stats = ref<any>({})
const userStatus = ref<any>(null)
const recommendationsRef = ref<any>(null)
const profile = ref<any>(null)

const calorieGoal = computed(() => {
  if (!profile.value?.bmr) return 500
  // 建议目标为 BMR 的 25% 左右作为额外训练消耗
  return Math.round(profile.value.bmr * 0.3)
})

// 新增：容量达标颜色逻辑（练得越好越绿，缺乏锻炼标红）
const getVolumeColor = (percentage: number) => {
  if (percentage >= 80) return '#67C23A' // 绿
  if (percentage >= 40) return '#E6A23C' // 橙
  return '#F56C6C' // 红
}

// 修改：变量名更替，并套用动态颜色函数
const volumeStatus = ref([
  { name: '胸部', percentage: 85, color: getVolumeColor(85) },
  { name: '腿部', percentage: 30, color: getVolumeColor(30) },
  { name: '核心', percentage: 60, color: getVolumeColor(60) }
])

const customColors = [
  { color: '#f56c6c', percentage: 20 },
  { color: '#e6a23c', percentage: 40 },
  { color: '#5cb87a', percentage: 60 },
  { color: '#1989fa', percentage: 80 },
  { color: '#6f7ad3', percentage: 100 },
]

const getBMIType = (bmi: number) => {
  if (bmi < 18.5) return 'warning'
  if (bmi < 24) return 'success'
  if (bmi < 28) return 'warning'
  return 'danger'
}

const getBMIText = (bmi: number) => {
  if (bmi < 18.5) return '偏瘦'
  if (bmi < 24) return '标准'
  if (bmi < 28) return '微胖'
  return '肥胖'
}

const fetchProfile = async () => {
  try {
    const res = await apiClient.get('/auth/profile/')
    profile.value = res.data
  } catch (err) {
    console.error('Failed to fetch profile:', err)
  }
}

const scrollToRecs = (targetScenario?: string) => {
  recommendationsRef.value?.$el.scrollIntoView({ behavior: 'smooth' })
  const finalScenario = targetScenario || (userStatus.value?.fatigue_level > 0.7 ? 'auto_adjust' : null)
  if (finalScenario) {
    recommendationsRef.value?.setScenario(finalScenario)
  }
}

const fetchUserStatus = async () => {
  try {
    const res = await apiClient.get('/recommendations/list/user_status/')
    userStatus.value = res.data
    // 修改：如果后端传来了 volume_stats，动态计算并赋值颜色
    if (res.data.volume_stats) {
      volumeStatus.value = res.data.volume_stats.map((item: any) => ({
        ...item,
        color: getVolumeColor(item.percentage)
      }))
    }
  } catch (err) {
    console.error('Failed to fetch user status:', err)
  }
}

const fetchTodayStats = async () => {
  loading.value = true
  try {
    const res = await apiClient.get('/analytics/daily-stats/today/')
    stats.value = res.data
  } catch (err) {
    console.error('Failed to fetch today stats:', err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchTodayStats()
  fetchUserStatus()
  fetchProfile()
})
</script>

<style scoped>
.dashboard-container {
  padding-bottom: 40px;
}

.welcome-banner {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 16px;
  padding: 40px;
  color: white;
  margin-bottom: 30px;
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
}

.banner-content h1 {
  font-size: 32px;
  margin-bottom: 12px;
}

.banner-content p {
  font-size: 18px;
  opacity: 0.9;
  margin-bottom: 24px;
}

.section {
  margin-bottom: 40px;
}

.section-title {
  font-size: 20px;
  font-weight: bold;
  margin-bottom: 20px;
  color: #303133;
}

.feature-card {
  height: 100%;
  cursor: pointer;
  transition: all 0.3s;
  text-align: center;
  padding: 10px;
}

.feature-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
  border-color: #409eff;
}

.card-icon {
  font-size: 40px;
  margin-bottom: 15px;
}

.feature-card h3 {
  margin: 10px 0;
  font-size: 16px;
}

.feature-card p {
  font-size: 13px;
  color: #909399;
}

.status-card {
  height: 100%;
}

.status-header {
  font-size: 14px;
  color: #909399;
  margin-bottom: 10px;
}

.status-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 15px;
}

.status-value span {
  font-size: 14px;
  font-weight: normal;
  color: #909399;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 20px;
}

.section-header .section-title {
  margin-bottom: 0;
}

.muscle-recovery-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin: 10px 0;
}

.muscle-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.m-name {
  font-size: 13px;
  color: #606266;
  min-width: 40px;
}

.muscle-item :deep(.el-progress) {
  flex: 1;
}

.status-footer {
  margin-top: 10px;
  font-size: 12px;
  color: #c0c4cc;
}

@media (max-width: 768px) {
  .welcome-banner {
    padding: 24px;
  }
}
</style>
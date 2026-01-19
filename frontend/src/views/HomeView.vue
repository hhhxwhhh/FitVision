<template>
  <div class="dashboard-container">
    <!-- 欢迎横幅 -->
    <div class="welcome-banner">
      <div class="banner-content">
        <h1>欢迎回来，{{ username }}! 👋</h1>
        <p>设定目标，坚持运动，AI 助你遇见更好的自己。</p>
        <div class="banner-actions">
          <el-button type="primary" size="large" @click="router.push('/training')">立即开始系统训练</el-button>
        </div>
      </div>
    </div>

    <!-- 快捷功能区 -->
    <section class="section">
      <h2 class="section-title">快捷入口</h2>
      <el-row :gutter="20">
        <el-col :xs="24" :sm="12" :md="6">
          <el-card class="feature-card" @click="router.push('/training?exercise_id=1')">
            <div class="card-icon">🦵</div>
            <h3>深蹲 AI 训练</h3>
            <p>实时矫正动作，科学计数</p>
          </el-card>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6">
          <el-card class="feature-card" @click="router.push('/training')">
            <div class="card-icon">📋</div>
            <h3>完成训练计划</h3>
            <p>执行今日安排的课程</p>
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

    <!-- 每日状态统计 -->
    <section class="section">
      <h2 class="section-title">今日状态</h2>
      <el-row :gutter="20" v-loading="loading">
        <el-col :xs="24" :sm="8">
          <el-card shadow="hover" class="status-card">
            <div class="status-header">已消耗热量</div>
            <div class="status-value">{{ stats.total_calories_burned || 0 }} <span>kcal</span></div>
            <el-progress :percentage="Math.min(100, ((stats.total_calories_burned || 0) / 500) * 100)"
              :show-text="false" />
            <div class="status-footer">目标: 500 kcal</div>
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
            <div class="status-header">完成动作数</div>
            <div class="status-value">{{ stats.completed_exercises || 0 }} <span>个</span></div>
            <el-progress :percentage="Math.min(100, ((stats.completed_exercises || 0) / 10) * 100)" :show-text="false"
              status="warning" />
            <div class="status-footer">目标: 10 个</div>
          </el-card>
        </el-col>
      </el-row>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import apiClient from '../api'

const router = useRouter()
const username = ref(localStorage.getItem('username') || '健身者')
const loading = ref(false)
const stats = ref<any>({})

const fetchTodayStats = async () => {
  loading.value = true
  try {
    const res = await apiClient.get('analytics/daily-stats/today/')
    stats.value = res.data
  } catch (err) {
    console.error('Failed to fetch today stats:', err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchTodayStats()
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

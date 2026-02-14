<template>
  <div class="recommendation-section">
    <div class="section-header">
      <h2 class="section-title">AI 为您推荐</h2>
      <div class="scenario-tabs">
        <el-radio-group v-model="scenario" size="small" @change="fetchRecommendations">
          <el-radio-button label="default">猜你喜欢</el-radio-button>
          <el-radio-button label="discovery">发现新鲜</el-radio-button>
          <el-radio-button label="daily_plan">进阶挑战</el-radio-button>
          <el-radio-button label="auto_adjust">动态调整</el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <el-row :gutter="20" v-loading="loading">
      <el-col :xs="24" :sm="12" :md="6" v-for="rec in recommendations" :key="rec.id">
        <el-card class="rec-card" :body-style="{ padding: '0px' }">
          <div class="algo-badge" :class="rec.algorithm">{{ getAlgoName(rec.algorithm) }}</div>
          <el-image 
            :src="rec.exercise.image_url || '/placeholder-exercise.jpg'" 
            class="rec-image"
            fit="cover"
          />
          <div class="rec-content">
            <h3 class="exercise-name">{{ rec.exercise.name }}</h3>
            <div class="exercise-meta">
              <el-tag size="small" type="info">{{ rec.exercise.target_muscle }}</el-tag>
              <el-tag size="small" :type="getDifficultyType(rec.exercise.difficulty)" class="ml-2">
                {{ rec.exercise.difficulty }}
              </el-tag>
            </div>
            <p class="rec-reason">{{ rec.reason }}</p>
            <div class="rec-actions">
              <el-button type="primary" link @click="startTraining(rec.exercise.id)">立即去练</el-button>
              <div class="feedback-btns">
                <el-tooltip content="不感兴趣" placement="top">
                  <el-button circle size="small" icon="CircleClose" @click="handleFeedback(rec, 'skip')" />
                </el-tooltip>
                <el-tooltip content="好评" placement="top">
                  <el-button circle size="small" icon="Star" @click="handleFeedback(rec, 'like')" />
                </el-tooltip>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { CircleClose, Star } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import apiClient from '../api'

const router = useRouter()
const loading = ref(false)
const scenario = ref('default')
const recommendations = ref<any[]>([])

const fetchRecommendations = async () => {
  loading.value = true
  try {
    const res = await apiClient.get(`/recommendations/list/get_personalized/`, {
      params: { scenario: scenario.value }
    })
    recommendations.value = res.data
  } catch (err) {
    console.error('Failed to fetch recommendations:', err)
  } finally {
    loading.value = false
  }
}

const getAlgoName = (algo: string) => {
  const map: any = {
    'cosine': '相似推荐',
    'ml_regression': '精准预测',
    'dl_sequence': '序列预测',
    'rl_adaptive': '状态感知',
    'popularity': '热门精选'
  }
  return map[algo] || 'AI 推荐'
}

const getDifficultyType = (diff: string) => {
  if (diff === 'beginner') return 'success'
  if (diff === 'intermediate') return 'warning'
  return 'danger'
}

const startTraining = (id: number) => {
  router.push(`/training?exercise_id=${id}`)
}

const handleFeedback = async (rec: any, action: string) => {
  try {
    await apiClient.post(`/recommendations/list/${rec.id}/feedback/`, { action })
    ElMessage.success(action === 'like' ? '感谢您的好评，AI 会为您推荐更多此类内容' : '已减少此类推荐')
    // 移除当前卡片
    recommendations.value = recommendations.value.filter(r => r.id !== rec.id)
  } catch (err) {
    ElMessage.error('操作失败')
  }
}

const setScenario = (newScenario: string) => {
  scenario.value = newScenario
  fetchRecommendations()
}

defineExpose({
  setScenario
})

onMounted(() => {
  fetchRecommendations()
})
</script>

<style scoped>
.recommendation-section {
  margin-top: 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.rec-card {
  position: relative;
  transition: all 0.3s;
  margin-bottom: 20px;
  overflow: hidden;
}

.rec-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 20px rgba(0,0,0,0.1) !important;
}

.algo-badge {
  position: absolute;
  top: 10px;
  left: 10px;
  z-index: 2;
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 10px;
  background: rgba(0,0,0,0.6);
  color: white;
  backdrop-filter: blur(4px);
}

.algo-badge.cosine { background: #3b82f6; }
.algo-badge.ml_regression { background: #8b5cf6; }
.algo-badge.dl_sequence { background: #ec4899; }
.algo-badge.rl_adaptive { background: #f59e0b; }
.algo-badge.popularity { background: #10b981; }
.algo-badge.rl_adaptive { background: #10b981; }

.rec-image {
  width: 100%;
  height: 160px;
  background-color: #f1f5f9;
}

.rec-content {
  padding: 16px;
}

.exercise-name {
  margin: 0 0 10px 0;
  font-size: 16px;
  font-weight: 700;
  color: var(--text-main);
}

.rec-reason {
  margin: 12px 0;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.4;
}

.rec-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 15px;
}

.feedback-btns {
  display: flex;
  gap: 8px;
}

.ml-2 { margin-left: 8px; }
</style>

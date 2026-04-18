<template>
  <!-- 推荐模块总容器：统一承载标题区、场景切换区和推荐内容区 -->
  <el-card class="recommendation-section module-shell" shadow="never">
    <template #header>
      <div class="section-header">
        <div class="header-top-row">
          <!-- 模块标题：第一行左对齐 -->
          <h2 class="section-title">AI为您推荐</h2>
          <!-- 动态库入口：第一行右对齐，并使用强调色突出 -->
          <el-button size="small" class="scenario-btn library-btn" @click="openExerciseLibrary">动态库</el-button>
        </div>

        <!-- 场景按钮组：第二行展示推荐类型选择 -->
        <div class="scenario-actions">
          <div class="scenario-library">
            <el-button
              v-for="option in scenarioOptions"
              :key="option.value"
              size="small"
              :type="scenario === option.value ? 'primary' : 'default'"
              class="scenario-btn"
              @click="setScenario(option.value)"
            >
              {{ option.label }}
            </el-button>
          </div>
        </div>
      </div>
    </template>

    <!-- 推荐卡片网格：默认两列展示，最多显示 maxItems 条 -->
    <div class="recommendation-grid" v-loading="loading">
      <el-card class="rec-card" :body-style="{ padding: '0px' }" v-for="rec in visibleRecommendations" :key="rec.id">
        <!-- 算法来源标识 -->
        <div class="algo-badge" :class="rec.algorithm">{{ getAlgoName(rec.algorithm) }}</div>
        <el-image
          :src="rec.exercise.image_url || '/placeholder-exercise.jpg'"
          class="rec-image"
          fit="cover"
        />
        <div class="rec-content">
          <!-- 动作名称与基础标签 -->
          <h3 class="exercise-name">{{ rec.exercise.name }}</h3>
          <div class="exercise-meta">
            <el-tag size="small" type="info">{{ rec.exercise.target_muscle }}</el-tag>
            <el-tag size="small" :type="getDifficultyType(rec.exercise.difficulty)" class="ml-2">
              {{ rec.exercise.difficulty }}
            </el-tag>
          </div>
          <!-- 推荐理由文案 -->
          <p class="rec-reason">{{ rec.reason }}</p>
          <div class="rec-actions">
            <!-- 快速开始训练 -->
            <el-button type="primary" link @click="startTraining(rec.exercise.id)">立即去练</el-button>
            <div class="feedback-btns">
              <!-- 用户反馈按钮：用于实时优化后续推荐 -->
              <el-tooltip content="不感兴趣" placement="top">
                <el-button circle size="small" :icon="CircleClose" @click="handleFeedback(rec, 'skip')" />
              </el-tooltip>
              <el-tooltip content="好评" placement="top">
                <el-button circle size="small" :icon="Star" @click="handleFeedback(rec, 'like')" />
              </el-tooltip>
            </div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 空状态：当前场景没有推荐时展示 -->
    <el-empty v-if="!loading && visibleRecommendations.length === 0" description="当前场景暂无推荐" />

    <!-- 超出显示上限时的提示文案 -->
    <div v-if="recommendations.length > visibleRecommendations.length" class="more-tip">
      已展示前 {{ visibleRecommendations.length }} 条推荐，可切换动态库查看更多。
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { CircleClose, Star } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import apiClient from '../api'

const props = withDefaults(defineProps<{
  maxItems?: number
}>(), {
  maxItems: 4
})

const router = useRouter()
const loading = ref(false)
const scenario = ref('default')
const recommendations = ref<any[]>([])

// 可切换推荐场景配置：按钮文案与后端查询参数一一对应
const scenarioOptions = [
  { label: '猜你喜欢', value: 'default' },
  { label: '发现新鲜', value: 'discovery' },
  { label: '进阶挑战', value: 'daily_plan' },
  { label: '动态调整', value: 'auto_adjust' }
]

// 仅展示前 maxItems 条，保证右侧推荐区高度可控
const visibleRecommendations = computed(() => recommendations.value.slice(0, props.maxItems))

// 拉取当前场景下的个性化推荐列表
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

// 将后端算法标识映射为用户可读名称
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

// 难度标记颜色映射：新手绿、中级橙、高级红
const getDifficultyType = (diff: string) => {
  if (diff === 'beginner') return 'success'
  if (diff === 'intermediate') return 'warning'
  return 'danger'
}

// 跳转到训练页，并带上动作 ID 作为初始化参数
const startTraining = (id: number) => {
  router.push(`/training?exercise_id=${id}`)
}

// 跳转至动作库（动态库）页面
const openExerciseLibrary = () => {
  router.push('/exercises')
}

// 用户反馈接口：提交后立即从当前列表移除该推荐
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

// 对外提供切场景能力，供父组件在特定情境下联动调用
const setScenario = (newScenario: string) => {
  scenario.value = newScenario
  fetchRecommendations()
}

defineExpose({
  setScenario
})

onMounted(() => {
  // 组件挂载后先拉取默认场景推荐
  fetchRecommendations()
})
</script>

<style scoped>
/* 推荐模块根容器 */
.recommendation-section {
  margin-top: 0;
}

/* 与首页其他模块保持统一的外层卡片间距 */
.module-shell :deep(.el-card__header) {
  padding: 10px 12px;
}

.module-shell :deep(.el-card__body) {
  padding: 12px;
}

/* 头部区域：左标题 + 右按钮区 */
.section-header {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-title {
  margin: 0;
  font-size: 18px;
}

.header-top-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

/* 场景按钮容器 */
.scenario-actions {
  display: flex;
  width: 100%;
}

/* 场景按钮组：第二行右对齐，间距更紧凑 */
.scenario-library {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  justify-content: flex-end;
  width: 100%;
}

/* 统一小按钮内边距 */
.scenario-btn {
  padding: 2px 8px;
}

/* 动态库按钮强调色：与普通场景按钮形成视觉区分 */
.library-btn {
  border-color: #f59e0b;
  color: #b45309;
  background: #fff7ed;
  font-weight: 600;
}

.library-btn:hover,
.library-btn:focus {
  border-color: #d97706;
  color: #92400e;
  background: #ffedd5;
}

/* 推荐卡片网格：桌面端两列 */
.recommendation-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.rec-card {
  position: relative;
  transition: all 0.3s;
  overflow: hidden;
}

/* 悬停轻微上浮，增强可交互感 */
.rec-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1) !important;
}

/* 算法来源徽标 */
.algo-badge {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 2;
  font-size: 9px;
  padding: 2px 6px;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  backdrop-filter: blur(4px);
}

.algo-badge.cosine { background: #3b82f6; }
.algo-badge.ml_regression { background: #8b5cf6; }
.algo-badge.dl_sequence { background: #ec4899; }
.algo-badge.rl_adaptive { background: #f59e0b; }
.algo-badge.popularity { background: #10b981; }

/* 卡片主图尺寸压缩以容纳两列三行 */
.rec-image {
  width: 100%;
  height: 88px;
  background-color: #f1f5f9;
}

.rec-content {
  padding: 10px;
}

.exercise-name {
  margin: 0 0 6px 0;
  font-size: 13px;
  font-weight: 700;
  color: var(--text-main);
}

/* 推荐理由文本 */
.rec-reason {
  margin: 6px 0;
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.3;
}

.rec-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 6px;
}

/* 右侧反馈按钮组 */
.feedback-btns {
  display: flex;
  gap: 6px;
}

/* 超出数量提示 */
.more-tip {
  margin-top: 6px;
  font-size: 11px;
  color: #909399;
}

.ml-2 { margin-left: 8px; }

/* 中小屏：按钮组对齐到左侧，避免标题挤压 */
@media (max-width: 900px) {
  .header-top-row {
    gap: 10px;
  }
}

/* 手机端：头部纵向排布，推荐卡片单列 */
@media (max-width: 600px) {
  .section-header {
    flex-direction: column;
    align-items: stretch;
  }

  .recommendation-grid {
    grid-template-columns: 1fr;
  }
}
</style>

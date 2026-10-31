<template>
  <div class="report-page">
    <div class="report-container">
      
      <div class="left-column">
        <div class="score-card" :class="getScoreClass(reportData.score)">
          <div class="score-header">本次表现</div>
          <div class="score-ring">
            <svg viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="45" class="bg-ring" />
              <circle cx="50" cy="50" r="45" class="progress-ring" 
                :style="{ strokeDashoffset: calculateDashOffset(reportData.score) }" />
            </svg>
            <div class="score-text">
              <span class="num">{{ reportData.score }}</span>
              <span class="label">综合评分</span>
            </div>
          </div>
          <div class="score-summary">
            <h2>{{ getScoreTitle(reportData.score) }}</h2>
            <p>击败了 {{ Math.min(99, Math.floor(reportData.score * 20)) }}% 的用户</p>
          </div>
        </div>

        <div class="action-buttons desktop-only">
          <el-button type="primary" size="large" class="home-btn" @click="goHome">
            返回数据中心 <el-icon class="el-icon--right"><DataLine /></el-icon>
          </el-button>
          <el-button :icon="Share" class="share-btn" @click="shareReport">分享训练报告</el-button>
          <el-button text class="sub-btn" @click="goHome">回到首页</el-button>
        </div>
      </div>

      <div class="right-column">
        <div class="ai-analysis-section">
          <div class="section-header">
            <div class="ai-icon">
              <div class="pulse"></div>
              <el-icon><MagicStick /></el-icon>
            </div>
            <h3>AI 教练深度复盘</h3>
          </div>
          
          <div class="analysis-content">
            <p class="ai-text" v-html="reportData.aiAnalysis"></p>
          </div>
          
          <div class="tags-row">
            <span v-for="(tag, index) in reportData.tags" :key="index" class="ai-tag">
              # {{ tag }}
            </span>
          </div>
        </div>

        <div class="stats-grid">
          <div class="stat-card">
            <div class="icon-wrapper time-icon"><el-icon><Timer /></el-icon></div>
            <div class="stat-info">
              <span class="label">训练时长</span>
              <span class="val">{{ reportData.duration }}<small>分</small></span>
            </div>
          </div>
          <div class="stat-card">
            <div class="icon-wrapper cal-icon"><el-icon><HotWater /></el-icon></div>
            <div class="stat-info">
              <span class="label">消耗热量</span>
              <span class="val">{{ reportData.calories }}<small>kcal</small></span>
            </div>
          </div>
          <div class="stat-card">
            <div class="icon-wrapper count-icon"><el-icon><Check /></el-icon></div>
            <div class="stat-info">
              <span class="label">完成动作</span>
              <span class="val">{{ reportData.completedCount }}<small>个</small></span>
            </div>
          </div>
          <div class="stat-card">
            <div class="icon-wrapper volume-icon"><el-icon><Odometer /></el-icon></div>
            <div class="stat-info">
              <span class="label">训练容量</span>
              <span class="val">{{ reportData.totalReps }}<small>次</small></span>
            </div>
          </div>
        </div>

        <div class="action-buttons mobile-only">
          <el-button type="primary" size="large" class="home-btn" @click="goHome">
            返回数据中心
          </el-button>
          <el-button :icon="Share" class="share-btn" @click="shareReport">分享训练报告</el-button>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { DataLine, Share, MagicStick, Timer, HotWater, Check, Odometer } from '@element-plus/icons-vue'

const router = useRouter()

const reportData = ref({
  score: 0,
  duration: 0,
  calories: 0,
  completedCount: 0,
  totalReps: 0,
  aiAnalysis: '正在生成详细的训练分析报告...',
  tags: [] as string[]
})

onMounted(() => {
  const storedData = localStorage.getItem('latestTrainingReport')
  if (storedData) {
    try {
      reportData.value = JSON.parse(storedData)
    } catch (e) {
      console.error('报告数据解析失败:', e)
      reportData.value.aiAnalysis = "报告数据读取错误，请在历史记录中查看。"
    }
  } else {
    reportData.value.aiAnalysis = "未找到最新的训练报告。"
  }
})

const calculateDashOffset = (score: number) => {
  const percent = Math.min(score, 5) / 5
  const circumference = 2 * Math.PI * 45
  return circumference * (1 - percent)
}

const getScoreClass = (score: number) => {
  if (score >= 4.5) return 'score-s'
  if (score >= 3.5) return 'score-a'
  return 'score-b'
}

const getScoreTitle = (score: number) => {
  if (score >= 4.8) return '健身战神'
  if (score >= 4.0) return '王者表现'
  if (score >= 3.0) return '表现出色'
  if (score >= 2.0) return '完成训练'
  return '继续加油'
}

const goHome = () => {
  router.replace('/')
}

const reportSummary = () => {
  const report = reportData.value
  return [
    'FitVision 训练报告',
    `综合评分：${report.score}`,
    `训练时长：${report.duration} 分钟`,
    `消耗热量：${report.calories} kcal`,
    `完成动作：${report.completedCount} 个 / ${report.totalReps} 次`,
    report.tags.length ? `关键词：${report.tags.join('、')}` : '',
  ]
    .filter(Boolean)
    .join('\n')
}

const copySummary = async () => {
  try {
    await navigator.clipboard.writeText(reportSummary())
    ElMessage.success('报告摘要已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败，请手动选择报告内容')
  }
}

const shareReport = async () => {
  const summary = reportSummary()
  if (navigator.share) {
    try {
      await navigator.share({ title: 'FitVision 训练报告', text: summary })
      return
    } catch (error) {
      if ((error as DOMException)?.name === 'AbortError') return
    }
  }
  await copySummary()
}
</script>

<style scoped>
.report-page {
  min-height: auto;
  padding: 8px 0 0;
  color: var(--fv-text);
  display: flex;
  justify-content: center;
  align-items: flex-start;
}

.report-container {
  width: 100%;
  max-width: 1400px;
  display: grid;
  grid-template-columns: 400px 1fr;
  gap: 28px;
}

/* === 左侧栏样式 === */
.left-column {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.score-card {
  position: relative;
  overflow: hidden;
  background: var(--fv-gradient);
  border-radius: 24px;
  padding: 44px 28px;
  text-align: center;
  border: 1px solid rgba(255, 255, 255, 0.18);
  box-shadow: var(--fv-shadow-glow);
  color: #fff;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

.score-card::after {
  content: '';
  position: absolute;
  inset: -40% -20% auto;
  height: 70%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.24), transparent 70%);
  pointer-events: none;
}

.score-header {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.78);
  text-transform: uppercase;
  letter-spacing: 0.16em;
  margin-bottom: 26px;
}

.score-ring {
  position: relative;
  width: 178px;
  height: 178px;
  margin-bottom: 26px;
}
.score-ring svg { transform: rotate(-90deg); width: 100%; height: 100%; }
.bg-ring { fill: none; stroke: rgba(255, 255, 255, 0.22); stroke-width: 9; }
.progress-ring {
  fill: none;
  stroke: #fff;
  stroke-width: 9;
  stroke-linecap: round;
  stroke-dasharray: 283;
  transition: stroke-dashoffset 1.2s cubic-bezier(0.22, 1, 0.36, 1);
  filter: none;
}
.score-s .progress-ring { stroke: #fff; }
.score-a .progress-ring { stroke: #e9e5ff; }
.score-b .progress-ring { stroke: #c7f5ff; }

.score-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
}
.score-text .num { font-size: 58px; font-weight: 800; line-height: 1; letter-spacing: -0.04em; }
.score-text .label { font-size: 12px; opacity: 0.72; margin-top: 6px; letter-spacing: 0.08em; }

.score-summary h2 { font-size: 26px; margin: 0 0 8px; font-weight: 700; }
.score-summary p { margin: 0; font-size: 14px; color: rgba(255, 255, 255, 0.78); }

/* === 右侧栏样式 === */
.right-column {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.ai-analysis-section {
  background: var(--fv-surface);
  border: 1px solid var(--fv-border);
  border-radius: 24px;
  padding: 34px;
  flex-grow: 1;
  box-shadow: var(--fv-shadow-sm);
}

.section-header { display: flex; align-items: center; gap: 14px; margin-bottom: 20px; }
.ai-icon {
  width: 46px;
  height: 46px;
  background: var(--fv-primary-soft);
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  position: relative;
}
.ai-analysis-section h3 { margin: 0; font-size: 20px; color: var(--fv-text); }

.ai-text {
  font-size: 16px;
  line-height: 1.85;
  color: var(--fv-text-2);
  margin-bottom: 26px;
  text-align: justify;
}
.ai-text :deep(b) {
  color: var(--fv-primary-strong);
  font-weight: 600;
  background: var(--fv-primary-soft);
  padding: 0 6px;
  border-radius: 6px;
}

.tags-row { display: flex; gap: 10px; flex-wrap: wrap; }
.ai-tag {
  background: var(--fv-surface-2);
  color: var(--fv-text-2);
  border: 1px solid var(--fv-border);
  font-size: 13px;
  padding: 7px 14px;
  border-radius: 999px;
}

/* 详细数据网格 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.stat-card {
  background: var(--fv-surface);
  border-radius: 18px;
  padding: 22px 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  border: 1px solid var(--fv-border);
  box-shadow: var(--fv-shadow-sm);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  min-height: 118px;
}
.stat-card:hover { transform: translateY(-3px); box-shadow: var(--fv-shadow-md); }

.icon-wrapper {
  width: 54px;
  height: 54px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  flex: none;
}
.time-icon { background: var(--fv-primary-soft); }
.cal-icon { background: rgba(245, 158, 11, 0.16); }
.count-icon { background: var(--fv-accent-soft); }
.volume-icon { background: rgba(16, 185, 129, 0.16); }

.stat-info { display: flex; flex-direction: column; min-width: 0; }
.stat-info .label { font-size: 12.5px; color: var(--fv-text-2); margin-bottom: 6px; }
.stat-info .val { font-size: 28px; font-weight: 700; color: var(--fv-text); line-height: 1; }
.stat-info .val small { font-size: 13px; margin-left: 3px; opacity: 0.55; font-weight: 400; }

/* 按钮样式 */
.action-buttons { display: flex; flex-direction: column; gap: 12px; }
.home-btn {
  height: 52px;
  font-size: 16px;
  font-weight: 600;
  border-radius: 14px;
  background: var(--fv-gradient);
  border: none;
  box-shadow: var(--fv-shadow-glow);
  color: #fff;
}
.home-btn:hover { opacity: 0.92; transform: translateY(-2px); }
.share-btn {
  border-radius: 14px;
  border-color: var(--fv-border);
  color: var(--fv-text-2);
}
.sub-btn { color: var(--fv-text-2); }
.sub-btn:hover { color: var(--fv-text); }

.mobile-only { display: none; }

/* 响应式适配 */
@media (max-width: 1200px) {
  .report-container {
    grid-template-columns: 1fr;
    max-width: 620px;
    gap: 20px;
  }

  .stats-grid { grid-template-columns: 1fr 1fr; }

  .desktop-only { display: none; }
  .mobile-only { display: flex; margin-top: 8px; }

  .score-card { height: auto; padding: 32px 24px; }
  .stat-card { padding: 18px; min-height: auto; }
  .stat-info .val { font-size: 22px; }
  .ai-analysis-section { padding: 24px; }
}

@media (max-width: 560px) {
  .stats-grid { grid-template-columns: 1fr; }
}
</style>

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
          <el-button text class="sub-btn" @click="goHome">回到首页</el-button>
        </div>
      </div>

      <div class="right-column">
        <div class="ai-analysis-section">
          <div class="section-header">
            <div class="ai-icon">
              <div class="pulse"></div>
              🧠
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
            <div class="icon-wrapper time-icon">⏱️</div>
            <div class="stat-info">
              <span class="label">训练时长</span>
              <span class="val">{{ reportData.duration }}<small>分</small></span>
            </div>
          </div>
          <div class="stat-card">
            <div class="icon-wrapper cal-icon">🔥</div>
            <div class="stat-info">
              <span class="label">消耗热量</span>
              <span class="val">{{ reportData.calories }}<small>kcal</small></span>
            </div>
          </div>
          <div class="stat-card">
            <div class="icon-wrapper count-icon">✅</div>
            <div class="stat-info">
              <span class="label">完成动作</span>
              <span class="val">{{ reportData.completedCount }}<small>个</small></span>
            </div>
          </div>
          <div class="stat-card">
            <div class="icon-wrapper volume-icon">⚖️</div>
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
        </div>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { DataLine } from '@element-plus/icons-vue'

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
  if (score >= 4.8) return '🔥 健身战神'
  if (score >= 4.0) return '👑 王者表现'
  if (score >= 3.0) return '🌟 表现出色'
  if (score >= 2.0) return '💪 完成训练'
  return '🏃 继续加油'
}

const goHome = () => {
  router.replace('/') 
}
</script>

<style scoped>
.report-page {
  min-height: 100vh;
  --milan-bg-main: #F5F2ED; /* 页面亮面背景 */
  --milan-bg-surface: #E5E0D8; /* 分隔/边框 */
  --milan-bg-soft: #EFE8DD; /* 弱强调背景 */
  --milan-text-primary: #3C2F2F; /* 主文本 */
  --milan-text-secondary: #7D756D; /* 辅助文本 */
  --milan-accent: #BEA47E; /* 主强调 */
  --milan-accent-soft: #D5C6B0; /* 次强调 */
  --milan-accent-deep: #9F8462; /* 深强调 */

  background: radial-gradient(circle at 50% 30%, #DCCFBE 0%, #4C403A 100%);
  color: var(--milan-bg-main);
  padding: 40px; /* 增加外边距 */
  display: flex;
  justify-content: center;
  align-items: flex-start; 
}

/* 🔥🔥🔥 核心修改：宽度解锁 95% 🔥🔥🔥 */
.report-container {
  width: 95%; 
  max-width: 1600px; /* 上限设为 1600px，适配大屏 */
  display: grid;
  grid-template-columns: 420px 1fr; /* 左侧加宽到 420px */
  gap: 40px; /* 间距拉大 */
  margin-top: 20px;
}

/* === 左侧栏样式 === */
.left-column {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.score-card {
  background: linear-gradient(145deg, rgba(76, 64, 58, 0.95), rgba(60, 47, 47, 0.95));
  border-radius: 24px;
  /* 增加内边距，撑大卡片 */
  padding: 50px 30px; 
  text-align: center;
  border: 1px solid rgba(229, 224, 216, 0.18);
  box-shadow: 0 20px 40px rgba(60, 47, 47, 0.35);
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

.score-header {
  font-size: 15px; color: #D5C6B0; text-transform: uppercase; letter-spacing: 1.5px;
  margin-bottom: 30px;
}

.score-ring {
  /* 圆环稍微加大 */
  position: relative; width: 180px; height: 180px; margin-bottom: 30px;
}
.score-ring svg { transform: rotate(-90deg); width: 100%; height: 100%; }
.bg-ring { fill: none; stroke: rgba(245, 242, 237, 0.12); stroke-width: 10; }
.progress-ring { fill: none; stroke-width: 10; stroke-linecap: round; stroke-dasharray: 283; transition: stroke-dashoffset 1.5s ease-out; }

/* 分数颜色 */
.score-s .progress-ring { stroke: #9F8462; filter: drop-shadow(0 0 8px rgba(159, 132, 98, 0.5)); }
.score-a .progress-ring { stroke: #BEA47E; filter: drop-shadow(0 0 8px rgba(190, 164, 126, 0.5)); }
.score-b .progress-ring { stroke: #D5C6B0; filter: drop-shadow(0 0 8px rgba(213, 198, 176, 0.45)); }

.score-text {
  position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
  display: flex; flex-direction: column;
}
.score-text .num { font-size: 60px; font-weight: 800; line-height: 1; } /* 字体加大 */
.score-text .label { font-size: 13px; opacity: 0.5; margin-top: 6px; }

.score-summary h2 { font-size: 30px; margin: 0 0 10px 0; font-weight: 700; }
.score-summary p { margin: 0; font-size: 15px; color: #D5C6B0; }

/* === 右侧栏样式 === */
.right-column {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* AI 分析板块 */
.ai-analysis-section {
  background: rgba(76, 64, 58, 0.62);
  border: 1px solid rgba(229, 224, 216, 0.2);
  border-radius: 24px;
  padding: 40px; /* 加大内边距 */
  flex-grow: 1; 
  backdrop-filter: blur(10px);
}

.section-header { display: flex; align-items: center; gap: 16px; margin-bottom: 24px; }
.ai-icon {
  width: 48px; height: 48px; background: rgba(190, 164, 126, 0.24);
  border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 24px;
  position: relative;
}
.ai-analysis-section h3 { margin: 0; font-size: 22px; color: #F5F2ED; }

.ai-text {
  font-size: 18px; line-height: 1.8; color: #E5E0D8; margin-bottom: 30px;
  text-align: justify;
}
.ai-text :deep(b) { color: #F5F2ED; font-weight: 600; background: rgba(213, 198, 176, 0.22); padding: 0 6px; border-radius: 4px; }

.tags-row { display: flex; gap: 14px; flex-wrap: wrap; }
.ai-tag {
  background: rgba(245, 242, 237, 0.08); color: #F5F2ED; border: 1px solid #D5C6B0;
  font-size: 14px; padding: 8px 16px; border-radius: 100px;
}

/* 详细数据网格 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr); 
  gap: 24px;
}

.stat-card {
  background: rgba(76, 64, 58, 0.75);
  border-radius: 20px; 
  padding: 24px 30px; /* 🔥 卡片内部空间加大 */
  display: flex; align-items: center; gap: 20px;
  border: 1px solid rgba(229, 224, 216, 0.14);
  transition: transform 0.2s;
  min-height: 130px; /* 增加高度 */
}
.stat-card:hover { transform: translateY(-5px); background: rgba(76, 64, 58, 0.9); }

.icon-wrapper {
  width: 64px; height: 64px; /* 图标加大 */
  border-radius: 20px; 
  display: flex; align-items: center; justify-content: center; font-size: 30px;
}
.time-icon { background: rgba(213, 198, 176, 0.2); }
.cal-icon { background: rgba(190, 164, 126, 0.2); }
.count-icon { background: rgba(159, 132, 98, 0.2); }
.volume-icon { background: rgba(229, 224, 216, 0.2); }

.stat-info { display: flex; flex-direction: column; }
.stat-info .label { font-size: 13px; color: #D5C6B0; margin-bottom: 6px; }
.stat-info .val { font-size: 32px; font-weight: 700; color: #F5F2ED; line-height: 1; } /* 数据字体加大 */
.stat-info .val small { font-size: 14px; margin-left: 2px; opacity: 0.6; font-weight: 400; }

/* 按钮样式 */
.action-buttons { display: flex; flex-direction: column; gap: 16px; }
.home-btn {
  height: 60px; font-size: 18px; font-weight: 600; border-radius: 16px;
  background: linear-gradient(90deg, #BEA47E 0%, #9F8462 100%); border: none;
  box-shadow: 0 4px 20px rgba(159, 132, 98, 0.35);
}
.home-btn:hover { opacity: 0.9; transform: translateY(-2px); }
.sub-btn { color: #D5C6B0; } .sub-btn:hover { color: #F5F2ED; }

.report-page :deep(.el-button--primary) {
  --el-button-bg-color: #BEA47E;
  --el-button-border-color: #BEA47E;
  --el-button-hover-bg-color: #9F8462;
  --el-button-hover-border-color: #9F8462;
  --el-button-active-bg-color: #9F8462;
  --el-button-active-border-color: #9F8462;
  --el-button-text-color: #F5F2ED;
}

.mobile-only { display: none; }

/* 📱 响应式适配：大屏幕以下自动调整 */
@media (max-width: 1200px) {
  .report-container {
    grid-template-columns: 1fr; 
    max-width: 600px;
    width: 100%;
    gap: 24px;
  }
  
  .stats-grid {
    grid-template-columns: 1fr 1fr;
  }

  .desktop-only { display: none; }
  .mobile-only { display: flex; margin-top: 12px; }
  
  .score-card { height: auto; padding: 30px; }
  .stat-card { padding: 20px; min-height: auto; }
  .stat-info .val { font-size: 24px; }
}
</style>
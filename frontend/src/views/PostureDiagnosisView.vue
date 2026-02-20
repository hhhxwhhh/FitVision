<template>
  <div class="posture-diagnosis">
    <el-card class="diagnosis-container">
      <div class="header-actions">
        <h2>姿态健康诊断 (AI 姿态建模)</h2>
        <div class="mode-switch">
          <el-radio-group v-model="currentMode" size="large">
            <el-radio-button label="front">正面全景</el-radio-button>
            <el-radio-button label="side">侧方视角</el-radio-button>
          </el-radio-group>
          <el-button type="primary" :loading="isAnalyzing" @click="handleAnalyze" class="action-btn">
            一键扫描分析
          </el-button>
        </div>
      </div>

      <el-row :gutter="20">
        <el-col :md="14" :xs="24">
          <div class="capture-session">
            <div class="video-preview">
              <video ref="videoElement" class="hidden-video"></video>
              <canvas ref="canvasElement" class="analysis-canvas"></canvas>
              <div v-if="!isLoaded" class="loading-overlay">
                <el-icon class="is-loading"><Loading /></el-icon>
                <span>准备底层 AI 模型...</span>
              </div>
            </div>
            <div class="guide-tips">
              <p>📸 请距离相机 <b>2-3 米</b> 站在画面中心，确全身关键点被识别。</p>
              <p>🕺 请保持直立放松，面朝或侧向相机 <b>3 秒</b> 后点击扫描。</p>
            </div>
          </div>
        </el-col>

        <el-col :md="10" :xs="24">
          <div v-if="report" class="report-panel">
            <div class="report-header">
               <div class="report-score" :class="getScoreClass(report.score)">
                   <div class="score-num">{{ report.score }}</div>
                   <div class="score-label">健康评分</div>
               </div>
               <div class="report-intro">
                   <h3>{{ report.summary }}</h3>
                   <p class="date">{{ new Date().toLocaleString() }}</p>
               </div>
            </div>

            <el-divider />

            <div class="detail-list">
                <div v-for="(item, idx) in report.details" :key="idx" class="detail-item">
                    <div class="detail-top">
                        <span class="detail-label">{{ item.label }}</span>
                        <el-tag :type="getTagType(item.status)" size="small">状况: {{ item.value }}</el-tag>
                    </div>
                    <div class="detail-advice">
                        <div class="advice-header">
                            <el-icon><InfoFilled /></el-icon>
                            <span>纠正建议：</span>
                        </div>
                        <p>{{ item.advice }}</p>
                    </div>
                </div>
            </div>
            
            <el-button type="success" size="large" block plain class="mt-4 w-full" @click="router.push('/exercises')">
                查看推荐动作 <el-icon class="ml-1"><ArrowRight /></el-icon>
            </el-button>
          </div>
          
          <el-empty v-else description="等待扫描数据中..." :image-size="120" />
        </el-col>
      </el-row>
    </el-card>

    <!-- History list -->
    <el-card class="mt-4 diagnosis-history">
       <template #header>最近 5 次扫描历史</template>
       <el-table :data="history" style="width: 100%" v-loading="loadingHistory">
           <el-table-column prop="created_at" label="时间" align="center">
               <template #default="scope">
                   {{ new Date(scope.row.created_at).toLocaleString() }}
               </template>
           </el-table-column>
           <el-table-column prop="diagnosis_type" label="类型" align="center">
               <template #default="scope">
                   <el-tag size="small">{{ scope.row.diagnosis_type === 'front' ? '正面' : '侧面' }}</el-tag>
               </template>
           </el-table-column>
           <el-table-column prop="score" label="评分" align="center">
               <template #default="scope">
                   <span :class="getScoreClass(scope.row.score)">{{ scope.row.score }}</span>
               </template>
           </el-table-column>
           <el-table-column prop="summary" label="核心评价" />
           <el-table-column label="操作" width="100" align="center">
               <template #default="scope">
                   <el-button link type="primary" @click="viewDetail(scope.row)">回顾报告</el-button>
               </template>
           </el-table-column>
       </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { Loading, InfoFilled, ArrowRight } from '@element-plus/icons-vue'
import { usePostureDiagnosis } from '@/composables/usePostureDiagnosis'
import apiClient from '@/api'
import { ElMessage } from 'element-plus'

const router = useRouter()
const {
  videoElement,
  canvasElement,
  isLoaded,
  isAnalyzing,
  currentMode,
  report,
  initPose,
  analyze,
  stop
} = usePostureDiagnosis()

const history = ref<any[]>([])
const loadingHistory = ref(false)

const getScoreClass = (score: number) => {
    if (score >= 90) return 'text-success font-bold'
    if (score >= 75) return 'text-warning font-bold'
    return 'text-danger font-bold'
}

const getTagType = (status: string) => {
    if (status === 'normal') return 'success'
    if (status === 'warning') return 'warning'
    return 'danger'
}

const handleAnalyze = async () => {
    await analyze()
    ElMessage.success('扫描完成，AI 报告已生成')
    fetchHistory()
}

const fetchHistory = async () => {
    loadingHistory.value = true
    try {
        const res = await apiClient.get('ai/posture-diagnosis/')
        // 处理分页响应
        const data = res.data.results || res.data
        if (Array.isArray(data)) {
            history.value = data.slice(0, 5)
        } else {
            console.error('Unexpected history data format', res.data)
        }
    } finally {
        loadingHistory.value = false
    }
}

const viewDetail = (row: any) => {
    report.value = {
        score: row.score,
        summary: row.summary,
        details: row.detailed_report
    }
}

onMounted(() => {
  initPose()
  fetchHistory()
})

onUnmounted(() => {
  stop()
})
</script>

<style scoped>
.posture-diagnosis {
    padding: 24px;
    max-width: 1200px;
    margin: 0 auto;
}

.header-actions {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
}

.mode-switch {
    display: flex;
    gap: 16px;
    align-items: center;
}

.capture-session {
    background: #f8fafc;
    border-radius: 12px;
    padding: 20px;
}

.video-preview {
    position: relative;
    border-radius: 8px;
    overflow: hidden;
    background: #000;
    min-height: 400px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.hidden-video {
    display: none;
}

.analysis-canvas {
    width: 100%;
    height: auto;
    display: block;
}

.loading-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    color: #fff;
    background: rgba(0,0,0,0.4);
    gap: 10px;
}

.guide-tips {
    margin-top: 16px;
    padding: 12px;
    background: #eff6ff;
    border-radius: 8px;
    color: #1d4ed8;
    font-size: 14px;
}

.guide-tips p {
    margin: 4px 0;
}

.report-panel {
    background: #fff;
    border-radius: 12px;
    padding: 20px;
    border: 1px solid #e2e8f0;
}

.report-header {
    display: flex;
    gap: 20px;
    align-items: center;
}

.report-score {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    border: 4px solid currentColor;
}

.score-num {
    font-size: 28px;
    line-height: 1;
}

.score-label {
    font-size: 12px;
}

.detail-list {
    display: flex;
    flex-direction: column;
    gap: 16px;
}

.detail-item {
    background: #f9fafb;
    border-radius: 8px;
    padding: 12px;
}

.detail-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}

.detail-label {
    font-weight: 600;
}

.detail-advice {
    font-size: 13px;
}

.advice-header {
    display: flex;
    align-items: center;
    gap: 4px;
    color: #64748b;
    margin-bottom: 2px;
}

.text-success { color: #10b981; }
.text-warning { color: #f59e0b; }
.text-danger  { color: #ef4444; }

.mt-4 { margin-top: 16px; }
.w-full { width: 100%; }
.ml-1 { margin-left: 4px; }
</style>

<template>
  <div class="plan-page">
    <div class="plan-container">
      
      <div class="ai-header-card">
        <div class="ai-avatar">
          <div class="pulse-ring" v-if="loading"></div>
          🧠
        </div>
        <div class="ai-greeting">
          <h2 v-if="!planData">准备好开始了吗？</h2>
          <h2 v-else>{{ planData.report_title }}</h2>
          
          <p v-if="!planData">告诉 AI 你的目标，为你定制专属 RAG 增强训练计划。</p>
          <p v-else v-html="planData.report_summary"></p>
        </div>
        
        <el-button 
          type="primary" 
          size="large"
          round 
          class="action-btn" 
          @click="showConfigDialog" 
          :loading="loading"
        >
          {{ planData ? '重新生成计划' : '生成专属计划' }}
          <el-icon class="el-icon--right" v-if="!loading"><MagicStick /></el-icon>
        </el-button>
      </div>

      <div class="dashboard-grid" v-if="planData">
        
        <div class="left-panel">
          <div class="panel-header">
            <div class="panel-title">📅 本周训练安排</div>
            <el-tag type="success" effect="dark" round>AI 已根据库存匹配动作</el-tag>
          </div>
          
          <div class="schedule-list">
            <div 
              v-for="(item, index) in planData.weekly_schedule" 
              :key="index"
              class="schedule-item"
              :class="{ 
                'training-day': item.type === 'training', 
                'rest-day': item.type !== 'training',
                'is-today': isToday(item.day)
              }"
            >
              <div class="day-wrapper">
                <div class="day-badge">{{ item.day }}</div>
                <div class="date-text">{{ getDayDate(item.day) }}</div>
              </div>

              <div class="content">
                <div class="title-row">
                  <div class="title">{{ item.title }}</div>
                  <div class="tags">
                    <el-tag size="small" v-if="isToday(item.day)" type="danger" effect="dark">Today</el-tag>
                    <el-tag size="small" v-else-if="item.type==='training'">训练日</el-tag>
                    <el-tag size="small" type="info" v-else>休息</el-tag>
                  </div>
                </div>
                
                <div class="status-text" v-if="item.type !== 'training'">
                  {{ item.status || '建议进行轻度拉伸或散步' }}
                </div>

                <div class="exercise-preview-list" v-else>
                  <div 
                    v-for="(ex, exIdx) in item.exercises" 
                    :key="exIdx" 
                    class="mini-exercise-card"
                    @click="showExerciseDetail(ex)"
                  >
                    <el-image 
                      v-if="ex.gif || ex.img" 
                      :src="ex.gif || ex.img" 
                      class="ex-thumb" 
                      fit="cover" 
                      loading="lazy"
                    />
                    <div v-else class="ex-thumb-placeholder">🏋️</div>
                    
                    <div class="ex-info">
                      <div class="ex-name">{{ ex.name }}</div>
                      <div class="ex-meta">{{ ex.sets }}组 × {{ ex.reps }}</div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="actions" v-if="item.type === 'training'">
                <el-button circle size="small" @click="openEditDialog(item, index)">
                  <el-icon><Edit /></el-icon>
                </el-button>
              </div>
            </div>
          </div>
        </div>

        <div class="right-panel">
          <div class="suggestion-card" v-for="(sug, idx) in planData.suggestions" :key="idx">
            <div class="card-icon">{{ sug.icon }}</div>
            <h3>{{ sug.title }}</h3>
            <p v-html="formatText(sug.content)"></p>
          </div>

          <div class="goal-progress">
            <div class="progress-header">
              <span>目标达成预测</span>
              <span>{{ planData.goal_progress }}%</span>
            </div>
            <el-progress 
              :percentage="planData.goal_progress" 
              :stroke-width="12" 
              striped 
              striped-flow 
              :color="customColors"
            />
          </div>
        </div>
      </div>

      <div v-else class="empty-state">
        <el-empty description="点击上方按钮，生成你的第一份 AI 计划" />
      </div>

    </div>

    <el-dialog v-model="configDialogVisible" title="定制你的训练计划" width="500px" align-center>
      <el-form label-position="top">
        <el-form-item label="当前目标">
          <el-radio-group v-model="userConfig.goal" fill="#3b82f6">
            <el-radio-button label="减脂" />
            <el-radio-button label="增肌" />
            <el-radio-button label="力量" />
          </el-radio-group>
        </el-form-item>
        
        <el-form-item label="训练频率 (每周几天)">
          <el-slider v-model="userConfig.days" :min="2" :max="6" show-stops :marks="{2:'2天', 4:'4天', 6:'6天'}" />
        </el-form-item>

        <el-form-item label="重点部位">
          <el-select v-model="userConfig.focus" placeholder="请选择">
            <el-option label="全身综合" value="全身" />
            <el-option label="胸肌与手臂" value="胸部,手臂" />
            <el-option label="背部与核心" value="背部,腹部" />
            <el-option label="臀腿专项" value="臀部,腿部" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="可用器材">
          <el-checkbox-group v-model="userConfig.equipment">
            <el-checkbox label="徒手" />
            <el-checkbox label="哑铃" />
            <el-checkbox label="杠铃" />
            <el-checkbox label="健身房固定器械" />
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="configDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="generatePlan" :loading="loading">
          🚀 开始生成 (预计20秒)
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editDialogVisible" title="调整训练内容" width="600px" align-center>
      <div v-if="editingItem" class="edit-container">
        <div class="edit-header">
          <h3>{{ editingItem.title }}</h3>
          <p class="sub-text">你可以自由调整组数、次数，或者删除不想要的动作。</p>
        </div>

        <div class="exercise-edit-list">
          <div v-for="(ex, idx) in editingItem.exercises" :key="idx" class="edit-row">
            <div class="row-left">
              <span class="idx">{{ idx + 1 }}</span>
              <span class="name">{{ ex.name }}</span>
            </div>
            <div class="row-inputs">
              <el-input-number v-model="ex.sets" size="small" :min="1" :max="10" /> 
              <span class="unit">组</span>
              <span class="x">×</span>
              <el-input v-model="ex.reps" size="small" style="width: 80px" />
            </div>
            <el-button type="danger" link icon="Delete" @click="removeExercise(idx)"></el-button>
          </div>
        </div>
        
        <div class="add-row">
          <el-button type="primary" link icon="Plus" @click="addEmptyExercise">添加自定义动作</el-button>
        </div>
      </div>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveEdit">保存修改</el-button>
      </template>
    </el-dialog>

  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { MagicStick, Edit, Delete, Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import apiClient from '../api'

// --- 类型定义 ---
interface Exercise {
  id?: number;
  name: string;
  gif?: string;
  img?: string;
  sets: number;
  reps: string | number;
  ai_desc?: string;
}

interface ScheduleItem {
  day: string;
  title: string;
  type: 'training' | 'rest';
  status: string;
  exercises: Exercise[];
}

interface PlanData {
  report_title: string;
  report_summary: string;
  weekly_schedule: ScheduleItem[];
  suggestions: any[];
  goal_progress: number;
}

// --- 状态 ---
const loading = ref(false)
const planData = ref<PlanData | null>(null)
const configDialogVisible = ref(false)
const editDialogVisible = ref(false)

// 用户配置 (弹窗用)
const userConfig = reactive({
  goal: '增肌',
  days: 4,
  focus: '全身',
  equipment: ['徒手', '哑铃'] // 默认值
})

// 编辑相关
const editingItem = ref<ScheduleItem | null>(null)
const editingIndex = ref(-1)

// 进度条颜色
const customColors = [
  { color: '#f56c6c', percentage: 20 },
  { color: '#e6a23c', percentage: 40 },
  { color: '#5cb87a', percentage: 60 },
  { color: '#1989fa', percentage: 80 },
  { color: '#6f7ad3', percentage: 100 },
]

// --- 逻辑方法 ---

// 1. 打开配置弹窗
const showConfigDialog = () => {
  configDialogVisible.value = true
}

// 2. 调用后端生成计划
const generatePlan = async () => {
  configDialogVisible.value = false
  loading.value = true
  
  // 构造发给后端的参数
  const payload = {
    goal: userConfig.goal,
    days: userConfig.days,
    focus: userConfig.focus,
    // 把数组转成逗号分隔字符串 "哑铃,徒手"
    equipment: userConfig.equipment.join(','),
    level: '中级', // 这里可以做成选项
    duration: 45
  }

  try {
    // 🔥 调用新的智能接口
    const res = await apiClient.post('/training/plan/create_smart/', payload, { timeout: 60000 })
    if (res.data) {
      planData.value = res.data
      ElMessage.success('专属计划生成成功！')
    }
  } catch (error: any) {
    console.error(error)
    ElMessage.error('AI 思考超时，请重试')
  } finally {
    loading.value = false
  }
}

// 3. 打开编辑弹窗
const openEditDialog = (item: ScheduleItem, index: number) => {
  // 深拷贝，防止修改影响原数据
  editingItem.value = JSON.parse(JSON.stringify(item))
  editingIndex.value = index
  editDialogVisible.value = true
}

// 4. 保存编辑
const saveEdit = () => {
  if (planData.value && editingIndex.value > -1 && editingItem.value) {
    planData.value.weekly_schedule[editingIndex.value] = editingItem.value
    editDialogVisible.value = false
    ElMessage.success('已更新今日安排')
  }
}

// 删除动作
const removeExercise = (idx: number) => {
  editingItem.value?.exercises.splice(idx, 1)
}
// 添加空动作
const addEmptyExercise = () => {
  editingItem.value?.exercises.push({
    name: '新动作',
    sets: 3,
    reps: '10次'
  })
}

// --- 辅助函数 ---
const formatText = (text: string) => {
  if (!text) return ''
  return text.replace(/\*\*(.*?)\*\*/g, '<span class="highlight-text">$1</span>')
}

const isToday = (dayStr: string) => {
  const days = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  const today = days[new Date().getDay()]
  return dayStr.includes(today)
}

const getDayDate = (dayName: string) => {
  const days = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  const today = new Date()
  const currentDayIndex = today.getDay()
  const targetDayIndex = days.indexOf(dayName)
  if (targetDayIndex === -1) return ''
  const diff = targetDayIndex - currentDayIndex
  const targetDate = new Date()
  targetDate.setDate(today.getDate() + diff)
  return `${targetDate.getMonth() + 1}/${targetDate.getDate()}`
}

const showExerciseDetail = (ex: Exercise) => {
  // 可以在这里做一个查看大图或视频的逻辑
  // 暂时先只打印
  console.log("查看动作", ex)
}
</script>

<style scoped>
/* 页面容器 */
.plan-page {
  min-height: calc(100vh - var(--header-height));
  padding: 0;
  display: flex;
  justify-content: center;
}

.plan-container { width: 100%; max-width: var(--max-width); padding: 32px 20px; }

/* 顶部 AI 卡片 */
.ai-header-card {
  background: white;
  border-radius: 24px;
  padding: 40px;
  display: flex; 
  align-items: center; 
  gap: 30px;
  margin-bottom: 32px;
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05), 0 2px 4px -2px rgb(0 0 0 / 0.05);
}

.ai-avatar {
  font-size: 56px;
  position: relative;
  width: 100px; height: 100px;
  background: var(--el-color-primary-light-9);
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}

.pulse-ring {
  position: absolute; width: 100%; height: 100%;
  border-radius: 50%; border: 3px solid var(--el-color-primary);
  animation: ripple 2s infinite;
}

.ai-greeting { flex: 1; }
.ai-greeting h2 { margin: 0 0 10px 0; font-size: 28px; color: var(--text-main); font-weight: 800; }
.ai-greeting p { margin: 0; color: var(--text-secondary); font-size: 16px; line-height: 1.6; }
/* 高亮样式穿透 */
.ai-greeting :deep(.highlight-text) { 
  color: var(--el-color-primary); font-weight: bold; background: var(--el-color-primary-light-9); padding: 0 4px; border-radius: 4px;
}

/* 核心网格 */
.dashboard-grid { display: grid; grid-template-columns: 1.6fr 1fr; gap: 30px; }

/* 左侧面板 */
.left-panel { background: white; border-radius: 24px; padding: 24px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05); }
.panel-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.panel-title { font-size: 20px; font-weight: 700; color: var(--text-main); }

.schedule-list { display: flex; flex-direction: column; gap: 20px; }

/* 日程卡片 */
.schedule-item {
  display: flex; gap: 20px; padding: 24px;
  border-radius: 16px; background: #f8fafc;
  border-left: 4px solid #e2e8f0;
  transition: all 0.3s ease;
}
.schedule-item:hover { transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1); }

/* 状态颜色 */
.schedule-item.training-day { border-left-color: #10b981; }
.schedule-item.rest-day { border-left-color: #94a3b8; }
.schedule-item.is-today { 
  border-left-color: var(--el-color-primary); 
  background: var(--el-color-primary-light-9);
}

.day-wrapper { text-align: center; width: 50px; flex-shrink: 0; }
.day-badge { font-size: 16px; font-weight: 800; color: var(--text-main); margin-bottom: 4px; }
.date-text { font-size: 12px; color: var(--text-secondary); }

.content { flex: 1; }
.title-row { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.title { font-size: 18px; font-weight: 700; color: var(--text-main); }

/* 动作列表（新） */
.exercise-preview-list {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px;
}

.mini-exercise-card {
  display: flex; align-items: center; gap: 12px;
  background: white; padding: 12px; border-radius: 12px;
  border: 1px solid #f1f5f9;
  cursor: pointer; transition: all 0.2s;
}
.mini-exercise-card:hover { border-color: var(--el-color-primary-light-5); background: var(--el-color-primary-light-9); }

.ex-thumb { width: 44px; height: 44px; border-radius: 8px; background: #f1f5f9; }
.ex-thumb-placeholder { width: 44px; height: 44px; border-radius: 8px; background: #f1f5f9; display: flex; align-items: center; justify-content: center; font-size: 20px; }

.ex-info { display: flex; flex-direction: column; }
.ex-name { font-size: 14px; font-weight: 600; color: var(--text-main); line-height: 1.2; }
.ex-meta { font-size: 12px; color: var(--text-secondary); }

.actions { display: flex; align-items: flex-start; }

/* 右侧建议 */
.right-panel { display: flex; flex-direction: column; gap: 20px; }
.suggestion-card { background: white; padding: 24px; border-radius: 20px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05); }
.card-icon { font-size: 28px; margin-bottom: 10px; }
.suggestion-card h3 { margin: 0 0 8px 0; font-size: 18px; font-weight: 700; color: var(--text-main); }
.suggestion-card p { margin: 0; font-size: 14px; color: var(--text-secondary); line-height: 1.6; }

.goal-progress { background: white; padding: 24px; border-radius: 20px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05); }
.progress-header { display: flex; justify-content: space-between; margin-bottom: 12px; font-weight: 600; color: var(--text-main); }

/* 编辑弹窗样式 */
.edit-container { padding: 10px; }
.edit-header { margin-bottom: 24px; border-bottom: 1px solid #f1f5f9; padding-bottom: 16px; }
.edit-header h3 { margin: 0; color: var(--text-main); font-size: 20px; }
.sub-text { margin: 8px 0 0 0; color: var(--text-secondary); font-size: 14px; }

.exercise-edit-list { display: flex; flex-direction: column; gap: 8px; }
.edit-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px; background: #f8fafc; border-radius: 12px;
}
.row-left { display: flex; align-items: center; gap: 12px; flex: 1; }
.idx { background: var(--el-color-primary-light-8); width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; color: var(--el-color-primary); font-weight: bold; }
.name { font-weight: 600; color: var(--text-main); }

.row-inputs { display: flex; align-items: center; gap: 8px; }
.unit, .x { color: var(--text-secondary); font-size: 13px; }
.add-row { margin-top: 20px; text-align: center; }

@keyframes ripple { 0% { transform: scale(1); opacity: 0.8; } 100% { transform: scale(1.5); opacity: 0; } }

@media (max-width: 768px) {
  .dashboard-grid { grid-template-columns: 1fr; }
  .ai-header-card { flex-direction: column; text-align: center; padding: 32px 20px; }
  .exercise-preview-list { grid-template-columns: 1fr; }
}
</style>
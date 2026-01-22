<template>
    <div class="page-container">
        <!-- Header Section -->
        <div class="page-header-row">
            <h1 class="page-title">智能训练中心</h1>
            <div class="header-tags">
                <el-tag v-if="sessionId" type="success" effect="dark" round class="status-tag">
                    <span class="dot accepted"></span> 会话进行中 #{{ sessionId }}
                </el-tag>
                <el-tag v-else type="info" round class="status-tag">
                    <span class="dot"></span> 未开始训练
                </el-tag>
            </div>
        </div>

        <el-row :gutter="24">
            <!-- Left Column: AI Vision & Plan -->
            <el-col :xs="24" :lg="15">
                <!-- AI Camera Card -->
                <el-card class="ai-display-card" :body-style="{ padding: 0 }">
                    <div class="ai-header">
                        <div class="ai-title">
                            <div class="pulse-indicator"></div>
                            AI 姿态识别
                        </div>
                        <el-tag size="small" effect="plain" class="tech-tag">MediaPipe Engine</el-tag>
                    </div>

                    <div class="camera-wrapper">
                        <PosePreview ref="posePreviewRef" :initial-exercise="selectedExerciseName"
                            @update:reps="handleAiReps" @update:score="handleAiScore" />

                        <div class="camera-overlay" v-if="!sessionId">
                            <div class="overlay-content">
                                <el-icon :size="64" class="camera-icon">
                                    <VideoCamera />
                                </el-icon>
                                <h3>准备开始</h3>
                                <p>启动训练会话以激活 AI 实时动作分析</p>
                            </div>
                        </div>
                    </div>

                    <div class="ai-footer">
                        <div class="ai-tip">
                            <el-icon>
                                <InfoFilled />
                            </el-icon>
                            <span>请保持全身在画面中，距离摄像头约 2-3 米，侧身或正对根据动作要求调整。</span>
                        </div>
                    </div>
                </el-card>

                <!-- Today's Plan Card -->
                <el-card class="plan-card" v-if="currentDayExercises.length">
                    <div class="card-header-styled">
                        <h3>📋 今日课表</h3>
                    </div>
                    <el-table :data="currentDayExercises" style="width: 100%"
                        :header-cell-style="{ background: '#f8fafc', color: '#475569' }">
                        <el-table-column prop="exercise_name" label="动作名称" min-width="140">
                            <template #default="scope">
                                <span class="exercise-name-cell">{{ scope.row.exercise_name }}</span>
                            </template>
                        </el-table-column>
                        <el-table-column prop="sets" label="组数" width="80" align="center">
                            <template #default="scope">
                                <el-tag size="small" type="info" effect="plain">{{ scope.row.sets }}组</el-tag>
                            </template>
                        </el-table-column>
                        <el-table-column prop="reps" label="每组次数" width="100" align="center" />
                        <el-table-column label="操作" width="100" align="center">
                            <template #default="scope">
                                <el-button size="small" type="primary" bg text icon="Edit"
                                    @click="fillRecordFromPlanExercise(scope.row)">
                                    填入
                                </el-button>
                            </template>
                        </el-table-column>
                    </el-table>
                </el-card>
            </el-col>

            <!-- Right Column: Control Panel -->
            <el-col :xs="24" :lg="9">
                <div class="control-column">
                    <el-card class="control-card shadow-sm">
                        <template #header>
                            <div class="panel-header">
                                <span>控制台</span>
                            </div>
                        </template>

                        <el-collapse v-model="activeSteps" accordion class="styled-collapse">
                            <!-- Step 1: Select Plan -->
                            <el-collapse-item name="plan">
                                <template #title>
                                    <div class="step-title">
                                        <div class="step-icon">1</div>
                                        <span>选择计划</span>
                                    </div>
                                </template>
                                <div class="step-content">
                                    <el-form label-position="top" class="compact-form">
                                        <el-form-item label="训练计划">
                                            <el-select v-model="selectedPlanId" placeholder="选择您的训练计划"
                                                style="width: 100%" size="large">
                                                <el-option v-for="plan in plans" :key="plan.id" :label="plan.name"
                                                    :value="plan.id" />
                                            </el-select>
                                        </el-form-item>

                                        <el-form-item label="训练日程">
                                            <el-select v-model="selectedDayId" placeholder="选择今日课程"
                                                :disabled="!selectedPlanId" style="width: 100%" size="large">
                                                <el-option v-for="day in planDays" :key="day.id"
                                                    :label="`第${day.day_number}天 - ${day.title}`" :value="day.id" />
                                            </el-select>
                                        </el-form-item>
                                    </el-form>
                                </div>
                            </el-collapse-item>

                            <!-- Step 2: Session Control -->
                            <el-collapse-item name="session">
                                <template #title>
                                    <div class="step-title">
                                        <div class="step-icon" :class="{ 'active': sessionId }">2</div>
                                        <span>会话控制</span>
                                        <el-tag v-if="sessionId" size="small" type="success"
                                            style="margin-left: auto">进行中</el-tag>
                                    </div>
                                </template>
                                <div class="step-content">
                                    <div v-if="!sessionId" class="start-state">
                                        <div class="empty-placeholder">
                                            <img src="https://img.icons8.com/color/96/dumbbell.png" alt="Training"
                                                width="64" />
                                            <p>准备好流汗了吗？</p>
                                        </div>
                                        <el-button type="primary" size="large" class="action-btn glow-effect"
                                            @click="handleStartSession" :loading="loading.start" block>
                                            🚀 开始训练
                                        </el-button>
                                    </div>
                                    <div v-else class="active-state">
                                        <div class="session-timer">
                                            <span>训练进行中</span>
                                        </div>
                                        <el-button @click="handleResetSession" type="danger" plain size="small"
                                            style="width: 100%; margin-top: 12px;">
                                            结束当前会话
                                        </el-button>
                                    </div>
                                </div>
                            </el-collapse-item>

                            <!-- Step 3: Record Action -->
                            <el-collapse-item name="record">
                                <template #title>
                                    <div class="step-title">
                                        <div class="step-icon">3</div>
                                        <span>动作打卡</span>
                                    </div>
                                </template>
                                <div class="step-content">
                                    <el-form :model="recordForm" label-position="top">
                                        <el-form-item label="当前动作">
                                            <el-input v-model="recordForm.exercise" placeholder="动作ID 或 从左侧填入">
                                                <template #prefix>
                                                    <el-icon>
                                                        <Trophy />
                                                    </el-icon>
                                                </template>
                                            </el-input>
                                            <div class="exercise-badge" v-if="selectedExerciseName">
                                                {{ selectedExerciseName }}
                                            </div>
                                        </el-form-item>

                                        <div class="form-grid">
                                            <el-form-item label="组数">
                                                <el-input-number v-model="recordForm.sets_completed" :min="1"
                                                    controls-position="right" style="width: 100%" />
                                            </el-form-item>
                                            <el-form-item label="时长 (秒)">
                                                <el-input-number v-model="recordForm.duration_seconds_actual" :min="0"
                                                    controls-position="right" style="width: 100%" />
                                            </el-form-item>
                                        </div>

                                        <el-form-item label="AI 动作评分">
                                            <div class="score-input-wrapper">
                                                <el-slider v-model="recordForm.form_score" :min="0" :max="100"
                                                    show-input :show-input-controls="false" />
                                            </div>
                                        </el-form-item>

                                        <el-button type="primary" @click="handleRecordExercise"
                                            :loading="loading.record" :disabled="!sessionId" block class="action-btn">
                                            ✅ 提交记录
                                        </el-button>
                                    </el-form>
                                </div>
                            </el-collapse-item>

                            <!-- Step 4: Finish -->
                            <el-collapse-item name="finish">
                                <template #title>
                                    <div class="step-title">
                                        <div class="step-icon">4</div>
                                        <span>完成总结</span>
                                    </div>
                                </template>
                                <div class="step-content">
                                    <el-form label-position="top">
                                        <el-form-item label="自我评分">
                                            <div class="rate-wrapper">
                                                <el-rate v-model="completeForm.performance_score" :max="5" size="large"
                                                    allow-half show-text :texts="['状态不佳', '一般', '还可以', '很棒', '超神']" />
                                            </div>
                                        </el-form-item>
                                        <el-button type="success" @click="handleCompleteSession"
                                            :loading="loading.complete" :disabled="!sessionId" block
                                            class="action-btn success-glow">
                                            🎉甚至完成训练
                                        </el-button>
                                    </el-form>
                                </div>
                            </el-collapse-item>
                        </el-collapse>
                    </el-card>
                </div>
            </el-col>
        </el-row>
    </div>
</template>

<script setup lang="ts">
import { reactive, ref, watch, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { VideoCamera, InfoFilled, Trophy, Edit } from '@element-plus/icons-vue'
import apiClient from '../api'
import PosePreview from '../components/ai/PosePreview.vue'

const route = useRoute()
const activeSteps = ref(['plan'])
const loading = reactive({
    start: false,
    record: false,
    complete: false,
    plans: false
})

const lastResponse = ref('')
const posePreviewRef = ref<any>(null)
const selectedExerciseName = ref('')

const handleAiReps = (count: number) => {
    recordForm.reps_completed = String(count);
};

const handleAiScore = (score: number) => {
    recordForm.form_score = score;
};

const sessionId = ref<number | null>(Number(localStorage.getItem('active_training_session')) || null)

const startForm = reactive({
    plan_id: '' as number | '',
    plan_day_id: '' as number | ''
})

const plans = ref<any[]>([])
const planDays = ref<any[]>([])
const selectedPlanId = ref<number | null>(null)
const selectedDayId = ref<number | null>(null)

const currentDay = computed(() => {
    return planDays.value.find((day) => day.id === selectedDayId.value)
})

const currentDayExercises = computed(() => {
    return currentDay.value?.exercises || []
})

const recordForm = reactive({
    session_id: sessionId.value || '',
    exercise: '',
    sets_completed: 0,
    reps_completed: '',
    weights_used: '',
    duration_seconds_actual: 0,
    form_score: 0
})

const completeForm = reactive({
    completed_exercises: 0,
    calories_burned: 0,
    performance_score: 0
})

watch(sessionId, (val) => {
    recordForm.session_id = val ? String(val) : ''
    if (val) {
        localStorage.setItem('active_training_session', String(val))
        activeSteps.value = ['session', 'record'] // Auto expand relevant steps
    } else {
        localStorage.removeItem('active_training_session')
    }
})

watch(selectedPlanId, async (val) => {
    startForm.plan_id = val ?? ''
    selectedDayId.value = null
    planDays.value = []
    if (!val) return
    await fetchPlanDays(val)
})

watch(selectedDayId, (val) => {
    startForm.plan_day_id = val ?? ''
})

const fetchPlans = async () => {
    loading.plans = true
    try {
        const res = await apiClient.get('training/plans/')
        const payload = res.data
        const planList = Array.isArray(payload) ? payload : (payload?.results || [])
        plans.value = planList.filter(Boolean)
    } catch (err: any) {
        ElMessage.error(err.response?.data?.error || '获取训练计划失败')
    } finally {
        loading.plans = false
    }
}

const fetchPlanDays = async (planId: number) => {
    try {
        const res = await apiClient.get(`training/plans/${planId}/days/`)
        const payload = res.data
        const dayList = Array.isArray(payload) ? payload : (payload?.results || [])
        planDays.value = dayList.filter(Boolean)
    } catch (err: any) {
        ElMessage.error(err.response?.data?.error || '获取训练计划日程失败')
    }
}

const parseNumberList = (value: string) => {
    if (!value) return []
    return value
        .split(',')
        .map((item) => Number(item.trim()))
        .filter((num) => !Number.isNaN(num))
}

const handleStartSession = async () => {
    loading.start = true
    try {
        const payload: Record<string, any> = {}
        if (startForm.plan_id) payload.plan_id = Number(startForm.plan_id)
        if (startForm.plan_day_id) payload.plan_day_id = Number(startForm.plan_day_id)

        const res = await apiClient.post('training/sessions/start/', payload)
        sessionId.value = res.data.id
        lastResponse.value = JSON.stringify(res.data, null, 2)
        ElMessage.success('训练会话已开始')
        activeSteps.value = ['record']
    } catch (err: any) {
        ElMessage.error(err.response?.data?.error || '开始会话失败')
    } finally {
        loading.start = false
    }
}

const handleRecordExercise = async () => {
    if (!sessionId.value) {
        ElMessage.warning('请先开始会话')
        return
    }
    if (!recordForm.exercise) {
        ElMessage.warning('请输入动作ID')
        return
    }

    loading.record = true
    try {
        const payload = {
            session_id: sessionId.value,
            exercise: Number(recordForm.exercise),
            sets_completed: recordForm.sets_completed,
            reps_completed: parseNumberList(recordForm.reps_completed),
            weights_used: parseNumberList(recordForm.weights_used),
            duration_seconds_actual: recordForm.duration_seconds_actual,
            form_score: recordForm.form_score
        }

        const res = await apiClient.post('training/exercise-records/', payload)
        lastResponse.value = JSON.stringify(res.data, null, 2)
        ElMessage.success('动作记录已提交')

        // 记录成功后重置 AI 计数
        if (posePreviewRef.value) {
            posePreviewRef.value.resetCount();
        }
    } catch (err: any) {
        ElMessage.error(err.response?.data?.error || '提交记录失败')
    } finally {
        loading.record = false
    }
}

const handleCompleteSession = async () => {
    if (!sessionId.value) return

    loading.complete = true
    try {
        const payload = {
            completed_exercises: completeForm.completed_exercises,
            calories_burned: completeForm.calories_burned,
            performance_score: completeForm.performance_score
        }

        const res = await apiClient.put(`training/sessions/${sessionId.value}/complete/`, payload)
        lastResponse.value = JSON.stringify(res.data, null, 2)
        ElMessage.success('训练会话已完成')
        sessionId.value = null
        activeSteps.value = ['plan']
    } catch (err: any) {
        ElMessage.error(err.response?.data?.error || '完成会话失败')
    } finally {
        loading.complete = false
    }
}

const handleResetSession = () => {
    sessionId.value = null
    ElMessage.info('已清除本地会话')
}

const fillRecordFromPlanExercise = (item: any) => {
    recordForm.exercise = String(item.exercise)
    selectedExerciseName.value = item.exercise_name || ''
    recordForm.sets_completed = item.sets || 0
    recordForm.reps_completed = item.reps ? String(item.reps) : ''
    recordForm.weights_used = item.weight ? String(item.weight) : ''
    recordForm.duration_seconds_actual = item.duration_seconds || 0
    // Switch to step 3
    activeSteps.value = ['record']
    ElMessage.success(`已填入: ${item.exercise_name || '动作'}`)
}

onMounted(async () => {
    await fetchPlans()
    const exerciseId = route.query.exercise_id
    const exerciseName = route.query.exercise_name

    if (exerciseId) {
        recordForm.exercise = String(exerciseId)
    }

    if (exerciseName) {
        selectedExerciseName.value = String(exerciseName)
    } else if (exerciseId) {
        const idMap: Record<string, string> = {
            '1': '深蹲',
            '2': '俯卧撑',
            '3': '开合跳'
        }
        if (idMap[String(exerciseId)]) {
            selectedExerciseName.value = idMap[String(exerciseId)]
        }
    }

    // Auto open session/record if active
    if (sessionId.value) {
        activeSteps.value = ['session', 'record']
    }
})
</script>

<script lang="ts">
export default {
    name: 'TrainingView'
}
</script>

<style scoped>
.page-container {
    max-width: 1200px;
    margin: 0 auto;
    padding-bottom: 60px;
}

.page-header-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
}

.status-tag {
    height: 32px;
    padding: 0 16px;
    font-weight: 600;
}

.dot {
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background-color: #94a3b8;
    margin-right: 6px;
    margin-bottom: 2px;
}

.dot.accepted {
    background-color: #22c55e;
}

/* AI Card */
.ai-display-card {
    background: #0f172a !important;
    border: 1px solid #1e293b;
    color: white;
    overflow: hidden;
    margin-bottom: 24px;
    border-radius: 16px;
}

.ai-header {
    background: rgba(255, 255, 255, 0.03);
    padding: 16px 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.ai-title {
    font-size: 16px;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 10px;
    color: #e2e8f0;
}

.pulse-indicator {
    width: 8px;
    height: 8px;
    background: #10b981;
    border-radius: 50%;
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0% {
        box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
    }

    70% {
        box-shadow: 0 0 0 8px rgba(16, 185, 129, 0);
    }

    100% {
        box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
    }
}

.camera-wrapper {
    position: relative;
    min-height: 520px;
    background: #020617;
    display: flex;
    align-items: center;
    justify-content: center;
}

.camera-overlay {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(15, 23, 42, 0.85);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10;
    backdrop-filter: blur(2px);
}

.overlay-content {
    text-align: center;
    color: #cbd5e1;
}

.camera-icon {
    margin-bottom: 16px;
    opacity: 0.8;
}

.overlay-content h3 {
    font-size: 20px;
    font-weight: 600;
    color: white;
    margin: 0 0 8px 0;
}

.ai-footer {
    padding: 12px 24px;
    background: rgba(255, 255, 255, 0.03);
    border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.ai-tip {
    font-size: 13px;
    color: #94a3b8;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* Plan Card */
.plan-card {
    border-radius: 16px;
    border: none;
    box-shadow: var(--card-shadow);
}

.card-header-styled {
    padding: 12px 0;
    border-bottom: 2px solid var(--border-color);
    margin-bottom: 16px;
}

.card-header-styled h3 {
    margin: 0;
    font-size: 18px;
    color: var(--text-main);
}

.exercise-name-cell {
    font-weight: 600;
    color: var(--text-main);
}

/* Control Panel */
.control-column {
    position: sticky;
    top: 90px;
}

.control-card {
    border-radius: 16px;
    border: none;
    overflow: hidden;
}

.panel-header {
    font-weight: 700;
    font-size: 16px;
    color: var(--text-main);
}

.styled-collapse {
    border-top: none;
    border-bottom: none;
}

:deep(.el-collapse-item__header) {
    height: 60px;
    font-size: 15px;
    border-bottom-color: var(--border-color);
}

.step-title {
    display: flex;
    align-items: center;
    gap: 12px;
    font-weight: 600;
    color: var(--text-main);
    width: 100%;
}

.step-icon {
    width: 28px;
    height: 28px;
    border-radius: 8px;
    background: #f1f5f9;
    color: #64748b;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    font-weight: 700;
    transition: all 0.3s;
}

.step-icon.active {
    background: var(--el-color-primary);
    color: white;
}

.step-content {
    padding: 24px 8px;
}

/* Form Styling */
.compact-form :deep(.el-form-item) {
    margin-bottom: 16px;
}

.form-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
}

.exercise-badge {
    margin-top: 8px;
    background: #eff6ff;
    color: var(--el-color-primary);
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
    display: inline-block;
}

.score-input-wrapper {
    padding: 0 8px;
}

.start-state {
    text-align: center;
    padding: 10px 0;
}

.empty-placeholder {
    margin-bottom: 20px;
}

.empty-placeholder p {
    color: var(--text-secondary);
    font-size: 14px;
    margin-top: 8px;
}

.active-state {
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-radius: 12px;
    padding: 16px;
    text-align: center;
}

.session-timer {
    font-weight: 600;
    color: #15803d;
    margin-bottom: 4px;
}

.action-btn {
    height: 48px;
    font-weight: 600;
    font-size: 16px;
    border-radius: 10px;
}

.glow-effect {
    box-shadow: 0 4px 14px 0 rgba(99, 102, 241, 0.39);
}

.success-glow {
    box-shadow: 0 4px 14px 0 rgba(74, 222, 128, 0.4);
}

.rate-wrapper {
    display: flex;
    justify-content: center;
    padding: 8px 0;
}
</style>
<template>
    <div class="training-container">
        <el-row :gutter="20">
            <!-- 左侧：AI 视图与动作列表 -->
            <el-col :xs="24" :md="14">
                <el-card class="panel ai-card">
                    <template #header>
                        <div class="header">
                            <span>AI 姿态检测预览</span>
                            <el-tag type="info">MediaPipe Pose</el-tag>
                        </div>
                    </template>
                    <PosePreview ref="posePreviewRef" :initial-exercise="recordForm.exercise"
                        @update:reps="handleAiReps" />
                    <div class="ai-tips">
                        <p>💡 提示：请确保全身在画面内，光线充足可提升识别精度。</p>
                    </div>
                </el-card>

                <el-card class="panel" v-if="currentDayExercises.length">
                    <template #header>
                        <div class="header">
                            <span>当日动作安排</span>
                        </div>
                    </template>
                    <el-table :data="currentDayExercises" style="width: 100%">
                        <el-table-column prop="exercise_name" label="动作" min-width="140" />
                        <el-table-column prop="sets" label="组数" width="70" />
                        <el-table-column prop="reps" label="次数" width="70" />
                        <el-table-column label="操作" width="80">
                            <template #default="scope">
                                <el-button size="small" type="primary" plain
                                    @click="fillRecordFromPlanExercise(scope.row)">
                                    填入
                                </el-button>
                            </template>
                        </el-table-column>
                    </el-table>
                </el-card>
            </el-col>

            <!-- 右侧：流程控制与表单 -->
            <el-col :xs="24" :md="10">
                <el-card class="panel control-panel">
                    <template #header>
                        <div class="header">
                            <span>训练控制台</span>
                            <el-tag v-if="sessionId" type="success">会话 ID: #{{ sessionId }}</el-tag>
                            <el-tag v-else type="info">未开始</el-tag>
                        </div>
                    </template>

                    <el-collapse v-model="activeSteps">
                        <el-collapse-item title="1. 选择计划" name="plan">
                            <el-form label-width="70px" size="small">
                                <el-form-item label="计划">
                                    <el-select v-model="selectedPlanId" placeholder="选择计划" clearable filterable
                                        style="width: 100%">
                                        <el-option v-for="plan in plans" :key="plan.id" :label="plan.name"
                                            :value="plan.id" />
                                    </el-select>
                                </el-form-item>
                                <el-form-item label="日程">
                                    <el-select v-model="selectedDayId" placeholder="选择日程" clearable filterable
                                        :disabled="!selectedPlanId" style="width: 100%">
                                        <el-option v-for="day in planDays" :key="day.id"
                                            :label="`第${day.day_number}天 ${day.title}`" :value="day.id" />
                                    </el-select>
                                </el-form-item>
                                <el-button @click="reloadPlans" :loading="loading.plans" icon="Refresh">刷新</el-button>
                            </el-form>
                        </el-collapse-item>

                        <el-collapse-item title="2. 会话状态" name="session">
                            <div class="session-actions">
                                <div v-if="!sessionId">
                                    <p class="hint">准备好了吗？点击开始进入正式训练。</p>
                                    <el-button type="primary" @click="handleStartSession" :loading="loading.start"
                                        block>
                                        开始本次训练
                                    </el-button>
                                </div>
                                <div v-else>
                                    <p class="success-hint">训练进行中，请根据下方列表进行运动。</p>
                                    <el-button @click="handleResetSession" size="small" type="info"
                                        plain>清除本地缓存</el-button>
                                </div>
                            </div>
                        </el-collapse-item>

                        <el-collapse-item title="3. 动作记录" name="record">
                            <el-form :model="recordForm" label-position="top" size="small">
                                <el-form-item label="当前动作" required>
                                    <el-input v-model="recordForm.exercise" placeholder="请从左侧列表填入动作 ID" />
                                </el-form-item>
                                <el-row :gutter="10">
                                    <el-col :span="12">
                                        <el-form-item label="完成组数">
                                            <el-input-number v-model="recordForm.sets_completed" :min="0"
                                                style="width: 100%" />
                                        </el-form-item>
                                    </el-col>
                                    <el-col :span="12">
                                        <el-form-item label="时长(秒)">
                                            <el-input-number v-model="recordForm.duration_seconds_actual" :min="0"
                                                style="width: 100%" />
                                        </el-form-item>
                                    </el-col>
                                </el-row>
                                <el-form-item label="动作质量评分 (AI 建议)">
                                    <el-slider v-model="recordForm.form_score" :min="0" :max="100" show-input />
                                </el-form-item>
                                <el-button type="primary" @click="handleRecordExercise" :loading="loading.record"
                                    :disabled="!sessionId" block>
                                    提交记录
                                </el-button>
                            </el-form>
                        </el-collapse-item>

                        <el-collapse-item title="4. 结束训练" name="finish">
                            <el-form label-position="top" size="small">
                                <el-form-item label="本次表现评分">
                                    <el-rate v-model="completeForm.performance_score" :max="100"
                                        :colors="['#99A9BF', '#F7BA2A', '#FF9900']" />
                                    <el-input-number v-model="completeForm.performance_score" :min="0" :max="100"
                                        style="margin-top: 10px" />
                                </el-form-item>
                                <el-button type="success" @click="handleCompleteSession" :loading="loading.complete"
                                    :disabled="!sessionId" block>
                                    训练完成，点此保存
                                </el-button>
                            </el-form>
                        </el-collapse-item>
                    </el-collapse>
                </el-card>

                <el-card v-if="lastResponse" class="panel debug-panel">
                    <template #header>
                        <div class="header">Debug 日志</div>
                    </template>
                    <pre class="response">{{ lastResponse }}</pre>
                </el-card>
            </el-col>
        </el-row>
    </div>
</template>

<script setup lang="ts">
import { reactive, ref, watch, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import apiClient from '../api'
import PosePreview from '../components/ai/PosePreview.vue'

const activeSteps = ref(['plan', 'session', 'record'])
const loading = reactive({
    start: false,
    record: false,
    complete: false,
    plans: false
})

const lastResponse = ref('')
const posePreviewRef = ref<any>(null)

const handleAiReps = (count: number) => {
    recordForm.reps_completed = String(count);
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

const reloadPlans = async () => {
    await fetchPlans()
}

const fetchPlans = async () => {
    loading.plans = true
    try {
        const res = await apiClient.get('training/plans/')
        plans.value = res.data || []
    } catch (err: any) {
        ElMessage.error(err.response?.data?.error || '获取训练计划失败')
    } finally {
        loading.plans = false
    }
}

const fetchPlanDays = async (planId: number) => {
    try {
        const res = await apiClient.get(`training/plans/${planId}/days/`)
        planDays.value = res.data || []
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
    recordForm.sets_completed = item.sets || 0
    recordForm.reps_completed = item.reps ? String(item.reps) : ''
    recordForm.weights_used = item.weight ? String(item.weight) : ''
    recordForm.duration_seconds_actual = item.duration_seconds || 0
    ElMessage.success('已填入动作记录表单')
}

onMounted(async () => {
    await fetchPlans()
})
</script>

<style scoped>
.training-container {
    max-width: 960px;
    margin: 24px auto 60px;
    display: flex;
    flex-direction: column;
    gap: 16px;
}

.panel {
    border-radius: 12px;
}

.header {
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.ai-card {
    margin-bottom: 20px;
}

.ai-tips {
    margin-top: 10px;
    color: #909399;
    font-size: 13px;
    text-align: center;
}

.control-panel :deep(.el-collapse-item__header) {
    font-weight: bold;
}

.session-actions {
    padding: 10px 0;
    text-align: center;
}

.hint {
    color: #909399;
    font-size: 13px;
    margin-bottom: 10px;
}

.success-hint {
    color: #67C23A;
    font-size: 14px;
    margin-bottom: 10px;
}

.debug-panel {
    margin-top: 20px;
    background-color: #f8f9fa;
}

.response {
    font-size: 12px;
    white-space: pre-wrap;
    max-height: 200px;
    overflow-y: auto;
}
</style>

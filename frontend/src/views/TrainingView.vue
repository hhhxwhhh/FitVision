<template>
    <div class="training-container">
        <el-card class="panel">
            <template #header>
                <div class="header">
                    <span>训练计划选择</span>
                </div>
            </template>

            <el-form label-width="120px" class="form">
                <el-form-item label="计划">
                    <el-select v-model="selectedPlanId" placeholder="可选" clearable filterable>
                        <el-option v-for="plan in plans" :key="plan.id" :label="plan.name" :value="plan.id" />
                    </el-select>
                </el-form-item>
                <el-form-item label="计划日">
                    <el-select v-model="selectedDayId" placeholder="可选" clearable filterable
                        :disabled="!selectedPlanId">
                        <el-option v-for="day in planDays" :key="day.id" :label="`第${day.day_number}天 ${day.title}`"
                            :value="day.id" />
                    </el-select>
                </el-form-item>
                <el-form-item>
                    <el-button @click="reloadPlans" :loading="loading.plans">刷新计划</el-button>
                </el-form-item>
            </el-form>
        </el-card>
        <el-card class="panel">
            <template #header>
                <div class="header">
                    <span>训练会话</span>
                    <el-tag v-if="sessionId" type="success">进行中：#{{ sessionId }}</el-tag>
                    <el-tag v-else type="info">未开始</el-tag>
                </div>
            </template>

            <el-form :model="startForm" label-width="120px" class="form">
                <el-form-item label="计划ID">
                    <el-input v-model="startForm.plan_id" placeholder="可选" :disabled="true" />
                </el-form-item>
                <el-form-item label="计划日ID">
                    <el-input v-model="startForm.plan_day_id" placeholder="可选" :disabled="true" />
                </el-form-item>
                <el-form-item>
                    <el-button type="primary" @click="handleStartSession" :loading="loading.start">
                        开始会话
                    </el-button>
                    <el-button @click="handleResetSession" :disabled="!sessionId">
                        清除会话
                    </el-button>
                </el-form-item>
            </el-form>
        </el-card>

        <el-card class="panel">
            <template #header>
                <div class="header">
                    <span>记录动作</span>
                </div>
            </template>

            <el-form :model="recordForm" label-width="120px" class="form">
                <el-form-item label="会话ID">
                    <el-input v-model="recordForm.session_id" placeholder="自动填充" :disabled="true" />
                </el-form-item>
                <el-form-item label="动作ID" required>
                    <el-input v-model="recordForm.exercise" placeholder="必填" />
                </el-form-item>
                <el-form-item label="完成组数">
                    <el-input-number v-model="recordForm.sets_completed" :min="0" />
                </el-form-item>
                <el-form-item label="每组次数">
                    <el-input v-model="recordForm.reps_completed" placeholder="例如: 10,8,12" />
                </el-form-item>
                <el-form-item label="每组重量(kg)">
                    <el-input v-model="recordForm.weights_used" placeholder="例如: 20,20,22.5" />
                </el-form-item>
                <el-form-item label="时长(秒)">
                    <el-input-number v-model="recordForm.duration_seconds_actual" :min="0" />
                </el-form-item>
                <el-form-item label="动作评分">
                    <el-input-number v-model="recordForm.form_score" :min="0" :max="100" />
                </el-form-item>
                <el-form-item>
                    <el-button type="primary" @click="handleRecordExercise" :loading="loading.record"
                        :disabled="!sessionId">
                        提交记录
                    </el-button>
                </el-form-item>
            </el-form>
        </el-card>

        <el-card class="panel" v-if="currentDayExercises.length">
            <template #header>
                <div class="header">
                    <span>当日动作列表</span>
                </div>
            </template>
            <el-table :data="currentDayExercises" style="width: 100%">
                <el-table-column prop="exercise_name" label="动作" min-width="160" />
                <el-table-column prop="sets" label="组数" width="80" />
                <el-table-column prop="reps" label="次数" width="80" />
                <el-table-column prop="duration_seconds" label="时长(秒)" width="100" />
                <el-table-column prop="weight" label="重量(kg)" width="100" />
                <el-table-column label="操作" width="120">
                    <template #default="scope">
                        <el-button size="small" @click="fillRecordFromPlanExercise(scope.row)">填入</el-button>
                    </template>
                </el-table-column>
            </el-table>
        </el-card>

        <el-card class="panel">
            <template #header>
                <div class="header">
                    <span>完成会话</span>
                </div>
            </template>

            <el-form :model="completeForm" label-width="120px" class="form">
                <el-form-item label="完成动作数">
                    <el-input-number v-model="completeForm.completed_exercises" :min="0" />
                </el-form-item>
                <el-form-item label="消耗卡路里">
                    <el-input-number v-model="completeForm.calories_burned" :min="0" />
                </el-form-item>
                <el-form-item label="表现评分">
                    <el-input-number v-model="completeForm.performance_score" :min="0" :max="100" />
                </el-form-item>
                <el-form-item>
                    <el-button type="success" @click="handleCompleteSession" :loading="loading.complete"
                        :disabled="!sessionId">
                        完成会话
                    </el-button>
                </el-form-item>
            </el-form>
        </el-card>

        <el-card v-if="lastResponse" class="panel">
            <template #header>
                <div class="header">
                    <span>最新返回</span>
                </div>
            </template>
            <pre class="response">{{ lastResponse }}</pre>
        </el-card>
    </div>
</template>

<script setup lang="ts">
import { reactive, ref, watch, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import apiClient from '../api'

const loading = reactive({
    start: false,
    record: false,
    complete: false,
    plans: false
})

const lastResponse = ref('')

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

.form {
    margin-top: 8px;
}

.response {
    font-size: 12px;
    white-space: pre-wrap;
}
</style>

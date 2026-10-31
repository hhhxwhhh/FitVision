<template>
  <div class="session-detail">
    <div class="detail-head">
      <el-button text @click="goBack">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
      <div class="head-main">
        <h1 class="page-title">{{ session?.plan_name || '自由训练' }}</h1>
        <p v-if="session" class="head-sub">{{ dateLabel }} · {{ statusLabel }}</p>
      </div>
    </div>

    <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" />

    <el-skeleton v-if="loading" :rows="6" animated />

    <template v-else-if="session">
      <div class="stat-grid">
        <div class="stat">
          <span>训练时长</span>
          <strong>{{ durationLabel }}</strong>
        </div>
        <div class="stat">
          <span>表现评分</span>
          <strong>{{ Math.round(session.performance_score) }}</strong>
        </div>
        <div class="stat">
          <span>完成动作</span>
          <strong>{{ session.completed_exercises }}/{{ session.total_exercises }}</strong>
        </div>
        <div class="stat">
          <span>消耗热量</span>
          <strong>{{ Math.round(session.calories_burned) }} kcal</strong>
        </div>
      </div>

      <div v-if="session.ai_tags?.length" class="tag-row">
        <el-tag v-for="tag in session.ai_tags" :key="tag" effect="plain">{{ tag }}</el-tag>
      </div>

      <section class="exercise-section">
        <div class="section-head">
          <h2>动作明细</h2>
          <span>{{ session.exercise_records?.length ?? 0 }} 个动作</span>
        </div>

        <el-empty
          v-if="!session.exercise_records?.length"
          description="这次训练还没有动作记录"
        />

        <div v-else class="exercise-list">
          <article
            v-for="record in session.exercise_records"
            :key="record.id"
            class="exercise-card"
          >
            <div class="exercise-top">
              <h3>{{ record.exercise_name }}</h3>
              <el-tag size="small" effect="plain">{{ Math.round(record.form_score) }} 分</el-tag>
            </div>
            <div class="exercise-meta">
              <span>{{ record.sets_completed }} 组</span>
              <span v-if="record.reps_completed?.length">
                次数 {{ record.reps_completed.join(' / ') }}
              </span>
              <span v-if="record.duration_seconds_actual > 0">
                时长 {{ Math.max(1, Math.round(record.duration_seconds_actual / 60)) }} 分钟
              </span>
              <span v-if="hasWeight(record)">重量 {{ weightLabel(record) }}</span>
            </div>
          </article>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import dayjs from 'dayjs'
import { ArrowLeft } from '@element-plus/icons-vue'
import apiClient from '../api'

interface ExerciseRecord {
  id: number
  exercise_name: string
  sets_completed: number
  reps_completed: number[] | null
  weights_used: number[] | null
  duration_seconds_actual: number
  form_score: number
}

interface SessionDetail {
  id: number
  plan_name: string | null
  start_time: string
  end_time: string | null
  is_completed: boolean
  total_exercises: number
  completed_exercises: number
  calories_burned: number
  performance_score: number
  ai_tags: string[] | null
  exercise_records: ExerciseRecord[]
}

const route = useRoute()
const router = useRouter()

const session = ref<SessionDetail | null>(null)
const loading = ref(false)
const error = ref('')

const fetchDetail = async () => {
  loading.value = true
  error.value = ''
  try {
    const { data } = await apiClient.get(`/training/sessions/${route.params.id}/`)
    session.value = data
  } catch (err) {
    error.value = '训练详情加载失败，可能记录不存在。'
    console.error('fetch session detail failed', err)
  } finally {
    loading.value = false
  }
}

onMounted(fetchDetail)

const goBack = () => {
  if (window.history.length > 1) router.back()
  else router.push('/history')
}

const dateLabel = computed(() =>
  session.value ? dayjs(session.value.start_time).format('YYYY 年 M 月 D 日 HH:mm') : '',
)

const statusLabel = computed(() => (session.value?.is_completed ? '已完成' : '未完成'))

const durationLabel = computed(() => {
  const item = session.value
  if (!item) return '—'
  if (!item.end_time) return '进行中'
  const minutes = Math.max(1, Math.round(dayjs(item.end_time).diff(dayjs(item.start_time), 'minute')))
  return `${minutes} 分钟`
})

const hasWeight = (record: ExerciseRecord) =>
  Array.isArray(record.weights_used) && record.weights_used.some((weight) => weight > 0)

const weightLabel = (record: ExerciseRecord) =>
  `${(record.weights_used ?? []).filter((weight) => weight > 0).join(' / ')} kg`
</script>

<style scoped>
.session-detail {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.detail-head {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.head-main .page-title {
  margin: 0 0 4px;
}

.head-sub {
  margin: 0;
  font-size: 13px;
  color: var(--fv-text-2);
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
}

.stat {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 16px 18px;
  border: 1px solid var(--fv-border);
  border-radius: var(--fv-radius-md);
  background: var(--fv-surface);
  box-shadow: var(--fv-shadow-sm);
}

.stat span {
  font-size: 12px;
  color: var(--fv-text-3);
}

.stat strong {
  font-size: 20px;
  font-weight: 800;
  color: var(--fv-text);
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.exercise-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  border-bottom: 1px solid var(--fv-border);
  padding-bottom: 6px;
}

.section-head h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 800;
  color: var(--fv-text);
}

.section-head span {
  font-size: 12px;
  color: var(--fv-text-3);
}

.exercise-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 10px;
}

.exercise-card {
  padding: 14px 16px;
  border: 1px solid var(--fv-border);
  border-radius: var(--fv-radius-md);
  background: var(--fv-surface);
  box-shadow: var(--fv-shadow-sm);
}

.exercise-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.exercise-top h3 {
  margin: 0;
  font-size: 14.5px;
  font-weight: 700;
  color: var(--fv-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.exercise-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 8px;
  font-size: 12.5px;
  color: var(--fv-text-2);
}
</style>

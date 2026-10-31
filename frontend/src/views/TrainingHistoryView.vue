<template>
  <div class="history-page">
    <header class="page-head">
      <div class="head-copy">
        <p class="fv-eyebrow">训练历史</p>
        <h1 class="page-title">每一次训练，都算数</h1>
        <p class="page-sub">
          共 {{ total }} 次训练 · 已完成 {{ completedCount }} 次
        </p>
      </div>
      <el-button type="primary" size="large" @click="router.push('/training')">
        <el-icon><VideoCamera /></el-icon>
        开始新训练
      </el-button>
    </header>

    <section v-if="!loading && sessions.length" class="stats-row">
      <article v-for="stat in statsCards" :key="stat.label" class="stat-card">
        <p class="stat-label">{{ stat.label }}</p>
        <p class="stat-value">{{ stat.value }}<small v-if="stat.unit">{{ stat.unit }}</small></p>
        <p class="stat-hint">{{ stat.hint }}</p>
      </article>
    </section>

    <div class="toolbar">
      <el-radio-group v-model="filter" size="default">
        <el-radio-button value="all">全部</el-radio-button>
        <el-radio-button value="completed">已完成</el-radio-button>
        <el-radio-button value="open">未完成</el-radio-button>
      </el-radio-group>

      <div class="toolbar-right">
        <el-button size="default" :disabled="!sessions.length" @click="exportCsv">
          <el-icon><Download /></el-icon>
          导出 CSV
        </el-button>
        <span v-if="!loading" class="toolbar-tip">按开始时间倒序</span>
      </div>
    </div>

    <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" />

    <div v-if="loading && sessions.length === 0" class="skeleton-list">
      <el-skeleton :rows="3" animated />
      <el-skeleton :rows="3" animated />
    </div>

    <template v-else-if="filteredGroups.length">
      <section v-for="group in filteredGroups" :key="group.key" class="month-group">
        <div class="month-head">
          <h2>{{ group.label }}</h2>
          <span>{{ group.sessions.length }} 次</span>
        </div>

        <ol class="timeline">
          <li v-for="item in group.sessions" :key="item.id" class="timeline-item">
            <div class="date-badge">
              <strong>{{ dayjs(item.start_time).format('DD') }}</strong>
              <span>{{ weekday(item.start_time) }}</span>
            </div>

            <article
              class="session-card"
              role="button"
              tabindex="0"
              @click="openDetail(item)"
              @keydown.enter="openDetail(item)"
              @keydown.space.prevent="openDetail(item)"
            >
              <div class="session-top">
                <div class="session-title">
                  <h3>{{ item.plan_name || '自由训练' }}</h3>
                  <el-tag v-if="item.is_completed" type="success" size="small" effect="plain">
                    已完成
                  </el-tag>
                  <el-tag v-else type="info" size="small" effect="plain">未完成</el-tag>
                </div>
                <span class="session-time">{{ dayjs(item.start_time).format('HH:mm') }}</span>
              </div>

              <div class="session-meta">
                <span><el-icon><Timer /></el-icon>{{ durationLabel(item) }}</span>
                <span><el-icon><Odometer /></el-icon>{{ scoreLabel(item) }}</span>
                <span><el-icon><Reading /></el-icon>{{ item.exercise_records_count }} 个动作</span>
                <span><el-icon><Sunny /></el-icon>{{ Math.round(item.calories_burned) }} kcal</span>
              </div>

              <div v-if="item.ai_tags?.length" class="session-tags">
                <el-tag
                  v-for="tag in item.ai_tags.slice(0, 3)"
                  :key="tag"
                  size="small"
                  effect="plain"
                >
                  {{ tag }}
                </el-tag>
              </div>
            </article>
          </li>
        </ol>
      </section>

      <div class="load-more">
        <el-button v-if="hasNext" :loading="loading" @click="loadMore">加载更多</el-button>
        <span v-else class="end-tip">已经看到全部训练记录</span>
      </div>
    </template>

    <el-empty v-else-if="!loading" description="还没有训练记录，开始第一次训练吧">
      <el-button type="primary" @click="router.push('/training')">开始训练</el-button>
    </el-empty>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import dayjs from 'dayjs'
import {
  Download,
  Odometer,
  Reading,
  Sunny,
  Timer,
  VideoCamera,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import apiClient from '../api'
import { datedFilename, downloadTextFile, toCsv } from '../utils/csv'
import { currentStreak, longestStreak, periodSummaries } from '../utils/trainingStats'

interface TrainingSession {
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
  exercise_records_count: number
}

type Filter = 'all' | 'completed' | 'open'

const router = useRouter()

const sessions = ref<TrainingSession[]>([])
const loading = ref(false)
const error = ref('')
const filter = ref<Filter>('all')
const page = ref(1)
const hasNext = ref(false)
const total = ref(0)

const WEEKDAYS = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
const weekday = (iso: string) => WEEKDAYS[new Date(iso).getDay()] ?? ''

const fetchPage = async (target: number) => {
  loading.value = true
  error.value = ''
  try {
    const { data } = await apiClient.get('/training/sessions/', { params: { page: target } })
    const results: TrainingSession[] = Array.isArray(data) ? data : (data.results ?? [])
    sessions.value = target === 1 ? results : [...sessions.value, ...results]
    hasNext.value = Array.isArray(data) ? false : Boolean(data.next)
    total.value = Array.isArray(data) ? results.length : (data.count ?? results.length)
    page.value = target
  } catch (err) {
    error.value = '训练历史加载失败，请稍后重试。'
    console.error('fetch training history failed', err)
  } finally {
    loading.value = false
  }
}

const loadMore = () => fetchPage(page.value + 1)

const openDetail = (item: TrainingSession) => router.push(`/history/${item.id}`)

onMounted(() => fetchPage(1))

const completedCount = computed(() => sessions.value.filter((item) => item.is_completed).length)

const summaries = computed(() => periodSummaries(sessions.value))

const streaks = computed(() => ({
  current: currentStreak(sessions.value),
  longest: longestStreak(sessions.value),
}))

const statsCards = computed(() => [
  {
    label: '近 7 天',
    value: summaries.value.week.count,
    unit: '次',
    hint: `已完成 ${summaries.value.week.completed} 次 · ${summaries.value.week.minutes} 分钟`,
  },
  {
    label: '本月训练',
    value: summaries.value.month.count,
    unit: '次',
    hint: `动作 ${summaries.value.month.completed} 次达标记录`,
  },
  {
    label: '本月时长',
    value: summaries.value.month.minutes,
    unit: '分钟',
    hint: `消耗 ${summaries.value.month.calories} kcal`,
  },
  {
    label: '本月均分',
    value: summaries.value.month.avgScore || '—',
    unit: summaries.value.month.avgScore ? '分' : '',
    hint: '按已完成评分场次平均',
  },
  {
    label: '连续训练',
    value: streaks.value.current,
    unit: '天',
    hint: `最长连续 ${streaks.value.longest} 天`,
  },
])

const exportCsv = () => {
  if (!sessions.value.length) return

  const rows = [...sessions.value].sort((a, b) => a.start_time.localeCompare(b.start_time))
  const csv = toCsv(rows, [
    { key: 'date', label: '日期', value: (row) => dayjs(row.start_time).format('YYYY-MM-DD') },
    { key: 'time', label: '开始时间', value: (row) => dayjs(row.start_time).format('HH:mm') },
    { key: 'plan', label: '训练计划', value: (row) => row.plan_name || '自由训练' },
    { key: 'duration', label: '时长(分钟)', value: (row) => durationMinutes(row) },
    { key: 'score', label: '表现评分', value: (row) => row.performance_score || '' },
    { key: 'exercises', label: '动作数', value: (row) => row.exercise_records_count },
    { key: 'calories', label: '消耗(kcal)', value: (row) => Math.round(row.calories_burned) },
    { key: 'status', label: '状态', value: (row) => (row.is_completed ? '已完成' : '未完成') },
    { key: 'tags', label: 'AI 标签', value: (row) => (row.ai_tags ?? []).join(' / ') },
  ])

  const ok = downloadTextFile(datedFilename('fitvision-training-history'), csv)
  if (ok) {
    ElMessage.success(`已导出 ${rows.length} 条训练记录`)
  } else {
    ElMessage.warning('当前环境不支持直接下载，请重试。')
  }
}

const filteredGroups = computed(() => {
  const list = sessions.value.filter((item) => {
    if (filter.value === 'all') return true
    return filter.value === 'completed' ? item.is_completed : !item.is_completed
  })

  const groups = new Map<string, { key: string; label: string; sessions: TrainingSession[] }>()
  for (const item of list) {
    const moment = dayjs(item.start_time)
    const key = moment.format('YYYY-MM')
    let group = groups.get(key)
    if (!group) {
      group = { key, label: moment.format('YYYY 年 M 月'), sessions: [] }
      groups.set(key, group)
    }
    group.sessions.push(item)
  }
  return [...groups.values()]
})

const durationMinutes = (item: TrainingSession) => {
  if (!item.end_time) return 0
  return Math.max(1, Math.round(dayjs(item.end_time).diff(dayjs(item.start_time), 'minute')))
}

const durationLabel = (item: TrainingSession) =>
  item.end_time ? `${durationMinutes(item)} 分钟` : '进行中'

const scoreLabel = (item: TrainingSession) =>
  item.performance_score > 0 ? `${Math.round(item.performance_score)} 分` : '—'
</script>

<style scoped>
.history-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 18px;
  flex-wrap: wrap;
}

.head-copy .page-title {
  margin: 6px 0 6px;
}

.page-sub {
  margin: 0;
  font-size: 13.5px;
  color: var(--fv-text-2);
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.stat-card {
  padding: 14px 16px;
  border: 1px solid var(--fv-border);
  border-radius: var(--fv-radius-md);
  background: var(--fv-surface);
}

.stat-label {
  margin: 0;
  font-size: 12px;
  color: var(--fv-text-3);
}

.stat-value {
  margin: 6px 0 4px;
  font-size: 24px;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: var(--fv-text);
}

.stat-value small {
  margin-left: 3px;
  font-size: 12px;
  font-weight: 600;
  color: var(--fv-text-2);
}

.stat-hint {
  margin: 0;
  font-size: 12px;
  color: var(--fv-text-2);
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

@media (max-width: 860px) {
  .stats-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 520px) {
  .toolbar-right {
    width: 100%;
    justify-content: space-between;
  }
}

.toolbar-tip {
  font-size: 12px;
  color: var(--fv-text-3);
}

.skeleton-list {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 8px;
  border: 1px solid var(--fv-border);
  border-radius: var(--fv-radius-lg);
  background: var(--fv-surface);
}

.month-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.month-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--fv-border);
}

.month-head h2 {
  margin: 0;
  font-size: 15px;
  font-weight: 800;
  letter-spacing: -0.01em;
  color: var(--fv-text);
}

.month-head span {
  font-size: 12px;
  color: var(--fv-text-3);
}

.timeline {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.timeline-item {
  display: flex;
  gap: 14px;
  align-items: stretch;
}

.date-badge {
  flex: none;
  width: 56px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  padding: 10px 0;
  border-radius: var(--fv-radius-md);
  border: 1px solid var(--fv-border);
  background: var(--fv-surface);
  box-shadow: var(--fv-shadow-sm);
}

.date-badge strong {
  font-size: 20px;
  font-weight: 800;
  line-height: 1;
  color: var(--fv-text);
}

.date-badge span {
  font-size: 11px;
  color: var(--fv-text-3);
}

.session-card {
  flex: 1;
  min-width: 0;
  padding: 14px 16px;
  border: 1px solid var(--fv-border);
  border-radius: var(--fv-radius-md);
  background: var(--fv-surface);
  box-shadow: var(--fv-shadow-sm);
  cursor: pointer;
  transition:
    transform 0.18s ease,
    border-color 0.18s ease,
    box-shadow 0.18s ease;
}

.session-card:hover {
  transform: translateY(-2px);
  border-color: var(--fv-primary);
  box-shadow: var(--fv-shadow-md);
}

.session-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.session-title {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.session-title h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: var(--fv-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-time {
  font-size: 12px;
  color: var(--fv-text-3);
  flex: none;
}

.session-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin-top: 10px;
  font-size: 12.5px;
  color: var(--fv-text-2);
}

.session-meta span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.session-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.load-more {
  display: flex;
  justify-content: center;
  padding: 8px 0 4px;
}

.end-tip {
  font-size: 12.5px;
  color: var(--fv-text-3);
}

@media (max-width: 620px) {
  .page-head {
    align-items: flex-start;
  }

  .date-badge {
    width: 48px;
  }

  .session-meta {
    gap: 10px;
  }
}
</style>

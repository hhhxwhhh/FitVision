<template>
  <div class="home" v-loading="loading">
    <section class="hero">
      <div class="hero-copy">
        <span class="fv-eyebrow">
          <span class="pulse-dot"></span>
          {{ greeting }} · {{ todayLabel }}
        </span>
        <h1>
          {{ greeting }}，<span class="gradient-text">{{ displayName }}</span>
        </h1>
        <p class="hero-sub">{{ heroSub }}</p>

        <div class="hero-actions">
          <el-button type="primary" size="large" @click="router.push('/training')">
            <el-icon><VideoPlay /></el-icon>
            开始训练
          </el-button>
          <el-button size="large" @click="router.push('/ai-plan')">
            <el-icon><MagicStick /></el-icon>
            生成 AI 计划
          </el-button>
          <el-button size="large" text @click="router.push('/posture-diagnosis')">
            姿态诊断
            <el-icon><ArrowRight /></el-icon>
          </el-button>
        </div>

        <div class="hero-meta">
          <span v-if="growthOverview.progress" class="fv-chip">
            <el-icon><Medal /></el-icon>
            Lv.{{ growthOverview.progress.level }} {{ growthOverview.progress.title }}
          </span>
          <span class="fv-chip">
            <el-icon><Calendar /></el-icon>
            本周 {{ weeklyTrainingDays }}/{{ weeklyGoalTarget }} 天
          </span>
          <span class="fv-chip">
            <el-icon><Trophy /></el-icon>
            连续 {{ currentStreak }} 天
          </span>
          <span class="fv-chip">
            <el-icon><Odometer /></el-icon>
            疲劳 {{ fatiguePercent }}%
          </span>
        </div>
      </div>

      <div class="readiness" :class="`tone-${readinessTone}`">
        <div class="readiness-ring">
          <svg viewBox="0 0 120 120" role="img" :aria-label="`今日状态 ${readiness} 分`">
            <circle class="ring-track" cx="60" cy="60" r="52" />
            <circle
              class="ring-value"
              cx="60"
              cy="60"
              r="52"
              :stroke-dasharray="`${readiness * 3.267} 326.7`"
            />
          </svg>
          <div class="ring-center">
            <strong>{{ readiness }}</strong>
            <span>今日状态</span>
          </div>
        </div>
        <div class="readiness-copy">
          <span class="readiness-label">{{ readinessLabel }}</span>
          <p>{{ readinessAdvice }}</p>

          <dl v-if="loadModel" class="load-model">
            <div class="load-model-item">
              <dt>负荷比</dt>
              <dd :class="`acwr-${acwrTone}`">{{ acwrText }}</dd>
            </div>
            <div class="load-model-item">
              <dt>体能-疲劳</dt>
              <dd>{{ tsbText }}</dd>
            </div>
            <div class="load-model-item">
              <dt>距上次</dt>
              <dd>{{ restText }}</dd>
            </div>
            <div class="load-model-item">
              <dt>建议强度</dt>
              <dd>{{ intensityText }}</dd>
            </div>
          </dl>

          <ul v-if="readinessReasons.length > 0" class="readiness-reasons">
            <li v-for="reason in readinessReasons" :key="reason">{{ reason }}</li>
          </ul>
        </div>
      </div>
    </section>

    <section class="insights">
      <div class="section-heading">
        <div>
          <h2>AI 教练洞察</h2>
          <p>基于最近 30 天训练数据实时生成</p>
        </div>
        <span class="section-badge">LIVE</span>
      </div>
      <div class="insight-grid">
        <article
          v-for="insight in insights"
          :key="insight.title"
          class="insight-card"
          :class="insight.tone"
        >
          <span class="insight-icon"><el-icon><component :is="insight.icon" /></el-icon></span>
          <div>
            <strong>{{ insight.title }}</strong>
            <p>{{ insight.body }}</p>
          </div>
        </article>
      </div>
    </section>

    <div class="home-grid">
      <div class="home-main">
        <section class="panel rhythm-panel">
          <div class="panel-head">
            <div>
              <h2>本周节奏</h2>
              <p>最近 7 天训练时长</p>
            </div>
            <div class="rhythm-total">
              <strong>{{ weeklyMinutes }}</strong>
              <span>分钟</span>
            </div>
          </div>

          <div class="rhythm">
            <div v-for="day in weekDays" :key="day.key" class="rhythm-day">
              <div class="rhythm-bar">
                <span
                  :class="{ today: day.isToday, rest: day.minutes === 0 }"
                  :style="{ height: `${day.height}%` }"
                ></span>
              </div>
              <span class="rhythm-label" :class="{ today: day.isToday }">{{ day.label }}</span>
            </div>
          </div>
        </section>

        <section class="stat-grid">
          <article v-for="stat in statCards" :key="stat.label" class="stat-card">
            <span class="stat-icon" :class="`tone-${stat.tone}`">
              <el-icon><component :is="stat.icon" /></el-icon>
            </span>
            <div class="stat-copy">
              <span>{{ stat.label }}</span>
              <strong>{{ stat.value }}<small>{{ stat.unit }}</small></strong>
              <em>{{ stat.hint }}</em>
            </div>
          </article>
        </section>

        <section class="panel achievements-panel">
          <div class="panel-head">
            <div>
              <h2>成就进度</h2>
              <p>每一次训练都在点亮新的节点</p>
            </div>
            <div class="achievement-head-actions">
              <span class="achievement-count">{{ unlockedCount }}/{{ achievementTotal }}</span>
              <el-button text size="small" @click="router.push('/growth')">查看全部</el-button>
            </div>
          </div>

          <div class="achievement-grid">
            <div
              v-for="item in achievementItems"
              :key="item.code"
              class="achievement"
              :class="{ unlocked: item.unlocked }"
            >
              <span class="achievement-dot">
                <el-icon><Check v-if="item.unlocked" /><Lock v-else /></el-icon>
              </span>
              <div>
                <strong>{{ item.title }}</strong>
                <span>{{ item.description }}</span>
              </div>
            </div>
          </div>
        </section>
      </div>

      <aside class="home-side">
        <AIRecommendations :max-items="4" />

        <section class="coach-card">
          <span class="coach-icon"><el-icon><MagicStick /></el-icon></span>
          <h3>不知道今天练什么？</h3>
          <p>让 AI 根据你的目标、疲劳与器械条件，生成一份可以直接执行的训练计划。</p>
          <el-button type="primary" class="coach-btn" @click="router.push('/ai-plan')">
            生成训练计划
            <el-icon><ArrowRight /></el-icon>
          </el-button>
        </section>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, type Component } from 'vue'
import { useRouter } from 'vue-router'
import {
  Aim,
  ArrowRight,
  Calendar,
  Check,
  Clock,
  DataLine,
  HotWater,
  Lock,
  MagicStick,
  Medal,
  Odometer,
  TrendCharts,
  Trophy,
  VideoPlay,
  Warning,
} from '@element-plus/icons-vue'
import apiClient from '../api'
import AIRecommendations from '../components/AIRecommendations.vue'

interface Insight {
  title: string
  body: string
  tone: 'positive' | 'warning' | 'neutral'
  icon: Component
}

const router = useRouter()
const loading = ref(false)
const stats = ref<any>({})
const userStatus = ref<any>({})
const profile = ref<any>({})
const dailyStats = ref<any[]>([])
const progress = ref<any[]>([])
const growthOverview = ref<any>({})

const growth = ref({
  weeklyTrainingDays: 0,
  currentStreak: 0,
  bestExercise: '',
  bestExerciseText: '',
})

const weeklyTrainingDays = computed(() =>
  Number(growthOverview.value?.weekly_goal?.completed_days ?? growth.value.weeklyTrainingDays),
)
const currentStreak = computed(() =>
  Number(growthOverview.value?.progress?.current_streak ?? growth.value.currentStreak),
)
const weeklyGoalTarget = computed(() =>
  Number(growthOverview.value?.weekly_goal?.target_sessions ?? 3),
)

const achievementItems = computed(() => {
  const preview = growthOverview.value?.achievements?.preview
  if (Array.isArray(preview) && preview.length > 0) return preview
  return [
    { code: 'first_session', title: '初次登场', description: '完成第一次训练', unlocked: false },
    { code: 'streak_3', title: '三日连击', description: '连续训练 3 天', unlocked: false },
    { code: 'weekly_3', title: '稳定节奏', description: '单周训练达到 3 天', unlocked: false },
    { code: 'form_90', title: '动作大师', description: '单个动作评分达到 90 分', unlocked: false },
  ]
})

const achievementTotal = computed(
  () => Number(growthOverview.value?.achievements?.total ?? achievementItems.value.length),
)

const displayName = computed(
  () => profile.value?.nickname || localStorage.getItem('username') || '健身者',
)

const todayLabel = new Intl.DateTimeFormat('zh-CN', {
  month: 'long',
  day: 'numeric',
  weekday: 'long',
}).format(new Date())

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 6) return '夜深了'
  if (hour < 12) return '早上好'
  if (hour < 18) return '下午好'
  return '晚上好'
})

const fatigue = computed(() => {
  const raw = Number(userStatus.value?.fatigue_level ?? 0)
  return Math.max(0, Math.min(1, Number.isFinite(raw) ? raw : 0))
})

const fatiguePercent = computed(() => Math.round(fatigue.value * 100))

const trainedToday = computed(() => Number(stats.value?.completed_sessions || 0) > 0)

const readiness = computed(() => {
  const serverScore = Number(growthOverview.value?.readiness?.score)
  if (Number.isFinite(serverScore) && serverScore > 0) return serverScore

  let score = 94 - fatigue.value * 55
  if (trainedToday.value) score -= 4
  if (currentStreak.value >= 3) score += 3
  if (weeklyTrainingDays.value >= 3) score += 2
  return Math.round(Math.max(25, Math.min(99, score)))
})

const readinessTone = computed(() => {
  const serverTone = growthOverview.value?.readiness?.tone
  if (typeof serverTone === 'string' && serverTone) return serverTone
  if (readiness.value >= 80) return 'excellent'
  if (readiness.value >= 62) return 'good'
  if (readiness.value >= 45) return 'moderate'
  return 'recover'
})

const readinessLabel = computed(() => {
  const serverLabel = growthOverview.value?.readiness?.label
  if (typeof serverLabel === 'string' && serverLabel) return serverLabel
  const labels: Record<string, string> = {
    excellent: '状态极佳',
    good: '适合训练',
    moderate: '中等强度',
    recover: '恢复优先',
  }
  return labels[readinessTone.value]
})

/**
 * 服务端返回的负荷模型（Banister 体能-疲劳 + ACWR + Foster 单调性）。
 * 只有带 `acwr` 字段时才说明是新版本接口，老接口/离线状态直接降级为 null。
 */
const loadModel = computed(() => {
  const raw = growthOverview.value?.readiness
  if (!raw || typeof raw !== 'object') return null
  const acwr = Number((raw as Record<string, unknown>).acwr)
  if (!Number.isFinite(acwr)) return null
  return raw as Record<string, number | string | string[]>
})

const readinessReasons = computed(() => {
  const reasons = loadModel.value?.reasons
  if (!Array.isArray(reasons)) return [] as string[]
  return reasons.filter((item): item is string => typeof item === 'string').slice(0, 3)
})

const acwrTone = computed(() => {
  const ratio = Number(loadModel.value?.acwr)
  if (!Number.isFinite(ratio)) return 'ok'
  if (ratio >= 1.5) return 'risk'
  if (ratio > 1.3 || ratio < 0.8) return 'watch'
  return 'ok'
})

const acwrText = computed(() => {
  const ratio = Number(loadModel.value?.acwr)
  return Number.isFinite(ratio) ? ratio.toFixed(2) : '—'
})

const tsbText = computed(() => {
  const tsb = Number(loadModel.value?.tsb)
  if (!Number.isFinite(tsb)) return '—'
  const rounded = Math.round(tsb)
  if (rounded > 0) return `体能 +${rounded}`
  if (rounded < 0) return `疲劳 ${rounded}`
  return '平衡'
})

const restText = computed(() => {
  const days = Number(loadModel.value?.rest_days)
  if (!Number.isFinite(days)) return '—'
  if (days < 0) return '暂无记录'
  if (days === 0) return '今天已练'
  return `${days} 天前`
})

const INTENSITY_LABELS: Record<string, string> = {
  rest: '主动恢复',
  light: '低强度',
  moderate: '中等强度',
  hard: '高强度',
}

const intensityText = computed(() => {
  const key = String(loadModel.value?.intensity ?? '')
  return INTENSITY_LABELS[key] ?? '按计划'
})

const topVolume = computed(() => {
  const volumes = userStatus.value?.volume_stats
  if (!Array.isArray(volumes) || volumes.length === 0) return null
  return [...volumes].sort((a, b) => Number(b.percentage) - Number(a.percentage))[0]
})

const readinessAdvice = computed(() => {
  const serverAdvice = growthOverview.value?.readiness?.advice
  if (typeof serverAdvice === 'string' && serverAdvice) return serverAdvice
  if (fatigue.value > 0.7) return '疲劳度偏高，建议安排 20 分钟低强度恢复训练。'
  if (topVolume.value && Number(topVolume.value.percentage) >= 80) {
    return `${topVolume.value.name}训练量较高，今天优先练其他部位或做主动恢复。`
  }
  if (readiness.value >= 80) return '身体信号良好，可以安排一次高质量力量或技术训练。'
  if (readiness.value >= 62) return '状态稳定，按计划完成中等强度训练即可。'
  return '先补充睡眠与水分，再用轻量活动唤醒身体。'
})

const heroSub = computed(() => {
  if (weeklyTrainingDays.value === 0) return '新的一周，从一次 15 分钟的训练开始。'
  if (weeklyTrainingDays.value >= weeklyGoalTarget.value) {
    return `本周已完成 ${weeklyTrainingDays.value} 天训练，节奏保持得很好。`
  }
  return `本周已训练 ${weeklyTrainingDays.value} 天，再完成 ${weeklyGoalTarget.value - weeklyTrainingDays.value} 天达成本周目标。`
})

const insights = computed<Insight[]>(() => {
  const items: Insight[] = []

  if (fatigue.value > 0.7) {
    items.push({
      title: '恢复优先级已提升',
      body: 'AI 检测到疲劳累积，今天的推荐会自动降低训练强度，并优先安排拉伸与核心稳定动作。',
      tone: 'warning',
      icon: Warning,
    })
  } else if (topVolume.value && Number(topVolume.value.percentage) >= 75) {
    items.push({
      title: `${topVolume.value.name}负荷偏高`,
      body: `本周${topVolume.value.name}训练量已接近上限，建议间隔 48 小时再练同一部位，让肌肉完成超量恢复。`,
      tone: 'warning',
      icon: Odometer,
    })
  }

  if (weeklyTrainingDays.value < weeklyGoalTarget.value) {
    items.push({
      title: `本周还差 ${weeklyGoalTarget.value - weeklyTrainingDays.value} 天`,
      body: `本周目标是训练 ${weeklyGoalTarget.value} 天。安排一次 20 分钟的训练，就能让习惯链条继续延伸。`,
      tone: 'neutral',
      icon: Calendar,
    })
  }

  if (growth.value.bestExercise) {
    items.push({
      title: `${growth.value.bestExercise}正在进步`,
      body: growth.value.bestExerciseText,
      tone: 'positive',
      icon: TrendCharts,
    })
  }

  if (currentStreak.value >= 3) {
    items.push({
      title: `连续 ${currentStreak.value} 天`,
      body: '连续性比单次强度更重要。今天保持轻量训练，也能守住这条连胜记录。',
      tone: 'positive',
      icon: Trophy,
    })
  }

  if (items.length === 0) {
    items.push({
      title: '从第一次训练开始',
      body: '完成一次训练后，这里会出现基于你的动作质量、训练量与恢复状态的个性化洞察。',
      tone: 'neutral',
      icon: Aim,
    })
  }

  return items.slice(0, 3)
})

interface WeekDay {
  key: string
  label: string
  minutes: number
  height: number
  isToday: boolean
}

const weekDays = computed<WeekDay[]>(() => {
  const byDate = new Map<string, any>()
  dailyStats.value.forEach((item) => byDate.set(String(item.date), item))
  const labels = ['日', '一', '二', '三', '四', '五', '六']
  const today = new Date()

  return Array.from({ length: 7 }, (_, index) => {
    const date = new Date(today)
    date.setDate(today.getDate() - (6 - index))
    const key = dateKey(date)
    const item = byDate.get(key)
    const minutes = Number(item?.total_duration_minutes || 0)
    return {
      key,
      label: labels[date.getDay()] ?? '',
      minutes,
      height: minutes > 0 ? Math.min(100, 24 + minutes * 1.6) : 7,
      isToday: key === dateKey(today),
    }
  })
})

const weeklyMinutes = computed(() =>
  weekDays.value.reduce((total, day) => total + day.minutes, 0),
)

const statCards = computed(() => [
  {
    label: '今日消耗',
    value: Math.round(Number(stats.value?.total_calories_burned || 0)),
    unit: 'kcal',
    hint: '训练与活动合计',
    tone: 'fire',
    icon: HotWater,
  },
  {
    label: '今日时长',
    value: Math.round(Number(stats.value?.total_duration_minutes || 0)),
    unit: 'min',
    hint: '建议每天 30 分钟',
    tone: 'clock',
    icon: Clock,
  },
  {
    label: '完成训练',
    value: Number(stats.value?.completed_sessions || 0),
    unit: '次',
    hint: '今天的训练会话',
    tone: 'session',
    icon: VideoPlay,
  },
  {
    label: '平均动作评分',
    value: Math.round(Number(stats.value?.average_form_score || 0)),
    unit: '分',
    hint: '由姿态识别计算',
    tone: 'score',
    icon: DataLine,
  },
])

const unlockedCount = computed(() => {
  const serverCount = Number(growthOverview.value?.achievements?.unlocked)
  if (Number.isFinite(serverCount) && serverCount >= 0) return serverCount
  return achievementItems.value.filter((item) => item.unlocked).length
})

function dateKey(date: Date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function shiftDays(date: Date, delta: number) {
  const next = new Date(date)
  next.setDate(next.getDate() + delta)
  return next
}

function computeStreak(trainedDates: Set<string>) {
  if (trainedDates.size === 0) return 0
  let cursor = new Date()
  if (!trainedDates.has(dateKey(cursor))) cursor = shiftDays(cursor, -1)
  let streak = 0
  while (trainedDates.has(dateKey(cursor))) {
    streak += 1
    cursor = shiftDays(cursor, -1)
  }
  return streak
}

function evaluateWeeklyProgress(items: any[]) {
  if (!items?.length) return { name: '', text: '', improved: false }

  const weekStart = dateKey(shiftDays(new Date(), -6))
  const grouped = new Map<number, any[]>()

  for (const item of items) {
    const id = Number(item.exercise) || Number(item.exercise_id)
    if (!id) continue
    const list = grouped.get(id) || []
    list.push(item)
    grouped.set(id, list)
  }

  let best: { name: string; score: number; text: string } | null = null
  for (const records of grouped.values()) {
    records.sort((a, b) => String(a.date).localeCompare(String(b.date)))
    const thisWeek = records.filter((record) => String(record.date) >= weekStart)
    if (thisWeek.length === 0) continue

    const latest = thisWeek[thisWeek.length - 1]
    const previous = records.filter((record) => String(record.date) < weekStart).slice(-1)[0]
    const scoreDelta =
      (Number(latest.best_form_score) || 0) - (Number(previous?.best_form_score) || 0)
    const previousVolume = Number(previous?.total_volume) || 0
    const currentVolume = Number(latest.total_volume) || 0
    const volumeDelta =
      previousVolume > 0 ? (currentVolume - previousVolume) / previousVolume : currentVolume > 0 ? 0.2 : 0
    const repsDelta = (Number(latest.max_reps) || 0) - (Number(previous?.max_reps) || 0)
    const totalGain = scoreDelta * 1.2 + volumeDelta * 30 + repsDelta * 1.8

    if (!best || totalGain > best.score) {
      best = {
        name: latest.exercise_name || '未命名动作',
        score: totalGain,
        text: `综合进步 +${Math.max(0, totalGain).toFixed(1)}，动作质量与训练量正在同步提升。`,
      }
    }
  }

  if (!best || best.score <= 0) return { name: '', text: '', improved: false }
  return { name: best.name, text: best.text, improved: true }
}

async function fetchDashboard() {
  loading.value = true
  try {
    const [profileRes, statsRes, statusRes, summaryRes, growthRes, progressRes] =
      await Promise.allSettled([
        apiClient.get('/auth/profile/'),
        apiClient.get('/analytics/daily-stats/today/'),
        apiClient.get('/recommendations/list/user_status/'),
        apiClient.get('/analytics/daily-stats/summary/?days=30'),
        apiClient.get('/growth/overview/'),
        apiClient.get('/analytics/exercise-progress/'),
      ])

    if (profileRes.status === 'fulfilled') profile.value = profileRes.value.data || {}
    if (statsRes.status === 'fulfilled') stats.value = statsRes.value.data || {}
    if (statusRes.status === 'fulfilled') userStatus.value = statusRes.value.data || {}
    if (growthRes.status === 'fulfilled') growthOverview.value = growthRes.value.data || {}

    if (summaryRes.status === 'fulfilled') {
      dailyStats.value = summaryRes.value.data?.daily_breakdown || []
    }
    if (progressRes.status === 'fulfilled') {
      progress.value = progressRes.value.data || []
    }

    const trainedDates = new Set(
      dailyStats.value
        .filter(
          (item) =>
            Number(item.total_duration_minutes || 0) > 0 ||
            Number(item.completed_sessions || 0) > 0 ||
            Number(item.completed_exercises || 0) > 0,
        )
        .map((item) => String(item.date)),
    )
    const weekStart = dateKey(shiftDays(new Date(), -6))
    const weeklyDays = dailyStats.value.filter(
      (item) => String(item.date) >= weekStart && trainedDates.has(String(item.date)),
    ).length

    const progressSummary = evaluateWeeklyProgress(progress.value)
    growth.value.weeklyTrainingDays = weeklyDays
    growth.value.currentStreak = computeStreak(trainedDates)
    growth.value.bestExercise = progressSummary.name
    growth.value.bestExerciseText = progressSummary.text
  } catch (error) {
    console.error('Failed to load dashboard:', error)
  } finally {
    loading.value = false
  }
}

onMounted(fetchDashboard)
</script>

<style scoped>
.home {
  display: flex;
  flex-direction: column;
  gap: 22px;
}

/* Hero ------------------------------------------------------------------ */
.hero {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(300px, 0.8fr);
  gap: 28px;
  align-items: center;
  padding: clamp(28px, 4vw, 48px);
  border-radius: var(--fv-radius-xl);
  border: 1px solid var(--fv-border);
  background:
    radial-gradient(700px 280px at 12% 0%, rgba(194, 65, 12, 0.12), transparent 62%),
    radial-gradient(600px 260px at 92% 100%, rgba(101, 163, 13, 0.1), transparent 60%),
    var(--fv-surface);
  box-shadow: var(--fv-shadow-md);
  overflow: hidden;
}

.hero::after {
  content: '';
  position: absolute;
  width: 260px;
  height: 260px;
  right: -80px;
  top: -120px;
  border-radius: 50%;
  border: 1px solid rgba(194, 65, 12, 0.2);
  box-shadow:
    0 0 0 40px rgba(194, 65, 12, 0.05),
    0 0 0 90px rgba(194, 65, 12, 0.04);
  pointer-events: none;
}

.hero-copy {
  position: relative;
  z-index: 1;
}

.pulse-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--fv-success);
  box-shadow: 0 0 0 4px rgba(21, 128, 61, 0.15);
  animation: pulse 2.4s ease-in-out infinite;
}

@keyframes pulse {
  0%,
  100% {
    box-shadow: 0 0 0 4px rgba(21, 128, 61, 0.15);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(21, 128, 61, 0.02);
  }
}

.hero h1 {
  margin: 14px 0 12px;
  font-size: clamp(34px, 4.2vw, 54px);
  line-height: 1.04;
  letter-spacing: -0.045em;
  font-weight: 900;
  color: var(--fv-text);
}

.hero-sub {
  margin: 0;
  max-width: 560px;
  font-size: 15.5px;
  line-height: 1.7;
  color: var(--fv-text-2);
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 26px;
}

.hero-actions :deep(.el-button) {
  height: 44px;
  padding: 0 18px;
  border-radius: 12px;
}

.hero-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 24px;
}

/* Readiness ------------------------------------------------------------- */
.readiness {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  padding: 24px;
  border-radius: var(--fv-radius-lg);
  border: 1px solid var(--fv-border);
  background: var(--fv-surface);
  text-align: center;
}

.readiness-ring {
  position: relative;
  width: 158px;
  height: 158px;
}

.readiness-ring svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.ring-track,
.ring-value {
  fill: none;
  stroke-width: 9;
}

.ring-track {
  stroke: var(--fv-surface-3);
}

.ring-value {
  stroke: var(--fv-primary);
  stroke-linecap: round;
  transition: stroke-dasharray 0.8s cubic-bezier(0.22, 1, 0.36, 1);
  filter: none;
}

.tone-excellent .ring-value {
  stroke: var(--fv-success);
  filter: none;
}

.tone-moderate .ring-value {
  stroke: var(--fv-warning);
  filter: none;
}

.tone-recover .ring-value {
  stroke: var(--fv-danger);
  filter: none;
}

.ring-center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
}

.ring-center strong {
  font-size: 44px;
  font-weight: 900;
  letter-spacing: -0.06em;
  line-height: 1;
  color: var(--fv-text);
}

.ring-center span {
  font-size: 11.5px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--fv-text-2);
}

.readiness-label {
  display: inline-flex;
  padding: 5px 12px;
  border-radius: 999px;
  background: var(--fv-primary-soft);
  color: var(--fv-primary);
  font-size: 12px;
  font-weight: 800;
}

.tone-excellent .readiness-label {
  background: rgba(21, 128, 61, 0.12);
  color: var(--fv-success);
}

.tone-moderate .readiness-label {
  background: rgba(180, 83, 9, 0.14);
  color: #b45309;
}

.tone-recover .readiness-label {
  background: rgba(239, 68, 68, 0.12);
  color: var(--fv-danger);
}

.readiness-copy p {
  margin: 8px 0 0;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--fv-text-2);
}

/* 负荷模型指标：4 个小格，纯边框分隔，不用卡片阴影 */
.load-model {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1px;
  margin: 14px 0 0;
  padding: 0;
  border: 1px solid var(--fv-border);
  border-radius: var(--fv-radius-sm);
  background: var(--fv-border);
  overflow: hidden;
}

.load-model-item {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 10px;
  background: var(--fv-surface);
}

.load-model dt {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: var(--fv-text-3);
}

.load-model dd {
  margin: 0;
  font-size: 12.5px;
  font-weight: 800;
  color: var(--fv-text);
  font-variant-numeric: tabular-nums;
}

.acwr-ok {
  color: var(--fv-success);
}

.acwr-watch {
  color: var(--fv-warning);
}

.acwr-risk {
  color: var(--fv-danger);
}

.readiness-reasons {
  margin: 10px 0 0;
  padding: 0;
  list-style: none;
  text-align: left;
  display: grid;
  gap: 4px;
}

.readiness-reasons li {
  position: relative;
  padding-left: 12px;
  font-size: 11.5px;
  line-height: 1.5;
  color: var(--fv-text-2);
}

.readiness-reasons li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 7px;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--fv-primary);
}

/* Insights -------------------------------------------------------------- */
.section-heading,
.panel-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
}

.section-heading h2,
.panel-head h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: var(--fv-text);
}

.section-heading p,
.panel-head p {
  margin: 4px 0 0;
  font-size: 12.5px;
  color: var(--fv-text-2);
}

.section-badge {
  padding: 4px 9px;
  border-radius: 999px;
  background: var(--fv-primary-soft);
  color: var(--fv-primary);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.14em;
}

.insight-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-top: 14px;
}

.insight-card {
  display: flex;
  gap: 12px;
  padding: 16px;
  border-radius: var(--fv-radius-md);
  border: 1px solid var(--fv-border);
  background: var(--fv-surface);
  box-shadow: var(--fv-shadow-sm);
}

.insight-icon {
  flex: none;
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border-radius: 11px;
  background: var(--fv-primary-soft);
  color: var(--fv-primary);
}

.insight-card.warning .insight-icon {
  background: rgba(180, 83, 9, 0.14);
  color: #d97706;
}

.insight-card.positive .insight-icon {
  background: rgba(21, 128, 61, 0.12);
  color: var(--fv-success);
}

.insight-card strong {
  display: block;
  font-size: 13.5px;
  color: var(--fv-text);
  margin-bottom: 4px;
}

.insight-card p {
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
  color: var(--fv-text-2);
}

/* Main grid ------------------------------------------------------------- */
.home-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(320px, 0.9fr);
  gap: 18px;
  align-items: start;
}

.home-main {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

.home-side {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

.panel {
  padding: 20px;
  border-radius: var(--fv-radius-lg);
  border: 1px solid var(--fv-border);
  background: var(--fv-surface);
  box-shadow: var(--fv-shadow-sm);
}

.rhythm-total {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.rhythm-total strong {
  font-size: 30px;
  font-weight: 900;
  letter-spacing: -0.05em;
  color: var(--fv-text);
}

.rhythm-total span {
  font-size: 12px;
  color: var(--fv-text-2);
}

.rhythm {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 10px;
  height: 150px;
  margin-top: 18px;
  align-items: end;
}

.rhythm-day {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  height: 100%;
}

.rhythm-bar {
  flex: 1;
  width: 100%;
  display: flex;
  align-items: flex-end;
  border-radius: 10px;
  background: var(--fv-surface-2);
  overflow: hidden;
}

.rhythm-bar span {
  width: 100%;
  min-height: 5px;
  border-radius: 10px;
  background: linear-gradient(180deg, #ea580c, var(--fv-primary));
  transition: height 0.6s cubic-bezier(0.22, 1, 0.36, 1);
}

.rhythm-bar span.rest {
  background: var(--fv-surface-3);
}

.rhythm-bar span.today {
  background: linear-gradient(180deg, #65a30d, var(--fv-primary));
  box-shadow: none;
}

.rhythm-label {
  font-size: 11px;
  color: var(--fv-text-3);
}

.rhythm-label.today {
  color: var(--fv-primary);
  font-weight: 800;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.stat-card {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 16px;
  border-radius: var(--fv-radius-md);
  border: 1px solid var(--fv-border);
  background: var(--fv-surface);
  box-shadow: var(--fv-shadow-sm);
}

.stat-icon {
  flex: none;
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border-radius: 11px;
  background: var(--fv-primary-soft);
  color: var(--fv-primary);
}

.stat-icon.tone-fire {
  background: rgba(239, 68, 68, 0.1);
  color: var(--fv-danger);
}

.stat-icon.tone-clock {
  background: rgba(101, 163, 13, 0.12);
  color: var(--fv-accent);
}

.stat-icon.tone-score {
  background: rgba(21, 128, 61, 0.12);
  color: var(--fv-success);
}

.stat-copy {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.stat-copy > span {
  font-size: 11.5px;
  color: var(--fv-text-2);
}

.stat-copy strong {
  font-size: 24px;
  font-weight: 900;
  letter-spacing: -0.04em;
  line-height: 1.15;
  color: var(--fv-text);
}

.stat-copy small {
  margin-left: 3px;
  font-size: 10.5px;
  font-weight: 600;
  color: var(--fv-text-3);
}

.stat-copy em {
  font-style: normal;
  font-size: 10.5px;
  color: var(--fv-text-3);
}

.achievement-head-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.achievement-count {
  font-size: 13px;
  font-weight: 800;
  color: var(--fv-primary);
}

.achievement-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 16px;
}

.achievement {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 12px;
  border-radius: 13px;
  border: 1px dashed var(--fv-border-strong);
  background: var(--fv-surface-2);
  opacity: 0.72;
}

.achievement.unlocked {
  border-style: solid;
  border-color: rgba(194, 65, 12, 0.28);
  background: var(--fv-primary-soft);
  opacity: 1;
}

.achievement-dot {
  flex: none;
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: var(--fv-surface);
  color: var(--fv-text-3);
}

.achievement.unlocked .achievement-dot {
  background: var(--fv-primary);
  color: #fff;
}

.achievement strong {
  display: block;
  font-size: 12.5px;
  color: var(--fv-text);
}

.achievement span {
  display: block;
  font-size: 10.5px;
  color: var(--fv-text-2);
}

/* Recommendation side --------------------------------------------------- */
.home-side :deep(.recommendation-section) {
  border-radius: var(--fv-radius-lg);
}

.coach-card {
  padding: 22px;
  border-radius: var(--fv-radius-lg);
  color: #fff;
  background: #1c1917;
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: var(--fv-shadow-md);
}

.coach-icon {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  border-radius: 13px;
  background: rgba(255, 255, 255, 0.16);
  font-size: 20px;
}

.coach-card h3 {
  margin: 16px 0 8px;
  font-size: 18px;
  font-weight: 800;
  letter-spacing: -0.02em;
}

.coach-card p {
  margin: 0 0 18px;
  font-size: 12.5px;
  line-height: 1.65;
  color: rgba(255, 255, 255, 0.78);
}

.coach-btn {
  width: 100%;
  background: #fff !important;
  border-color: #fff !important;
  color: #4338ca !important;
}

.coach-btn:hover {
  background: rgba(255, 255, 255, 0.9) !important;
}

@media (max-width: 1100px) {
  .hero {
    grid-template-columns: 1fr;
  }

  .readiness {
    flex-direction: row;
    text-align: left;
    justify-content: flex-start;
  }

  .readiness-ring {
    width: 122px;
    height: 122px;
    flex: none;
  }

  .ring-center strong {
    font-size: 34px;
  }

  .home-grid {
    grid-template-columns: 1fr;
  }

  .insight-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .home {
    gap: 16px;
  }

  .hero {
    padding: 24px 20px;
  }

  .hero-actions :deep(.el-button) {
    flex: 1;
    min-width: 120px;
  }

  .stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .achievement-grid {
    grid-template-columns: 1fr;
  }

  .readiness {
    align-items: center;
    flex-direction: column;
    text-align: center;
  }
}

@media (max-width: 420px) {
  .stat-grid {
    grid-template-columns: 1fr;
  }

  .rhythm {
    gap: 6px;
  }
}
</style>

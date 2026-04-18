<template>
  <div class="dashboard-container">
    <transition name="banner-collapse">
      <div v-if="showWelcomeBanner" class="welcome-banner">
        <div class="banner-content">
          <h1>欢迎回来，{{ username }}! 👋</h1>
          <p>设定目标，坚持运动，AI 助你遇见更好的自己。</p>
        </div>
      </div>
    </transition>

    <el-alert
      v-if="userStatus?.fatigue_level > 0.7"
      title="AI 检测到您处于疲劳状态"
      type="warning"
      description="建议今天进行低强度恢复训练。我们已为您准备了专门的放松动作。"
      show-icon
      class="mb-6"
    >
      <template #default>
        <div class="mt-2">
          <el-button type="warning" size="small" @click="scrollToRecs('auto_adjust')">查看恢复建议</el-button>
        </div>
      </template>
    </el-alert>

    <div class="dashboard-grid">
      <div class="left-panel">
        <el-card class="left-overview-shell" shadow="never" v-loading="growthLoading">
          <section class="section growth-section">
          <div class="section-header growth-header">
            <h2 class="section-title">成长看板</h2>
            <el-tag type="success" effect="dark">{{ growth.positiveMessage }}</el-tag>
          </div>

          <el-row :gutter="16" class="growth-cards">
            <el-col :xs="24" :sm="8">
              <el-card shadow="hover" class="growth-card">
                <div class="growth-card-title">本周已训练</div>
                <div class="growth-card-value">{{ growth.weeklyTrainingDays }} <span>天</span></div>
                <div class="growth-card-sub">目标: 3 天起步，5 天优秀</div>
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="8">
              <el-card shadow="hover" class="growth-card">
                <div class="growth-card-title">连续打卡</div>
                <div class="growth-card-value">{{ growth.currentStreak }} <span>天</span></div>
                <div class="growth-card-sub">保持节奏，连击越高越强</div>
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="8">
              <el-card shadow="hover" class="growth-card growth-action-card">
                <div class="growth-card-title">继续训练</div>
                <div class="growth-card-value growth-action">解锁进阶动作</div>
                <div class="growth-action-buttons">
                  <el-button size="small" type="primary" @click="router.push('/training')">今日训练</el-button>
                  <el-button size="small" @click="router.push('/posture-diagnosis')">AI姿态诊断</el-button>
                </div>
              </el-card>
            </el-col>
          </el-row>

          <el-card class="achievement-card" shadow="never">
            <div class="achievement-title">成就系统</div>
            <div class="achievement-list">
              <div v-for="item in growth.achievements" :key="item.key" class="achievement-item">
                <el-tag :type="item.unlocked ? 'success' : 'info'" effect="plain" size="small">
                  {{ item.unlocked ? '已达成' : '进行中' }}
                </el-tag>
                <div class="achievement-content">
                  <div class="achievement-name">{{ item.title }}</div>
                  <div class="achievement-desc">{{ item.description }}</div>
                </div>
              </div>
            </div>
          </el-card>

          <el-card class="module-shell compact-status-shell" shadow="never">
            <template #header>
              <div class="module-header section-header">
                <h2 class="section-title">今日状态</h2>
                <el-tag v-if="profile?.bmi" :type="getBMIType(profile.bmi)" size="small" effect="plain" class="bmi-tag">
                  BMI: {{ profile.bmi.toFixed(1) }} ({{ getBMIText(profile.bmi) }})
                </el-tag>
              </div>
            </template>
            <div class="status-grid status-inline-four" v-loading="loading">
              <el-card shadow="hover" class="status-card">
                <div class="status-header-row">
                  <div class="status-header">
                    已消耗热量
                    <span class="status-inline-value">{{ stats.total_calories_burned || 0 }} <span>kcal</span></span>
                  </div>
                  <div class="status-note-inline">目标: {{ calorieGoal }} kcal</div>
                </div>
                <el-progress :percentage="Math.min(100, ((stats.total_calories_burned || 0) / calorieGoal) * 100)"
                  :show-text="false" :color="customColors" />
              </el-card>

              <el-card shadow="hover" class="status-card">
                <div class="status-header-row">
                  <div class="status-header">
                    累计训练时长
                    <span class="status-inline-value">{{ stats.total_duration_minutes || 0 }} <span>min</span></span>
                  </div>
                  <div class="status-note-inline">目标: 30 min</div>
                </div>
                <el-progress :percentage="Math.min(100, ((stats.total_duration_minutes || 0) / 30) * 100)"
                  :show-text="false" status="success" />
              </el-card>

              <el-card shadow="hover" class="status-card">
                <div class="status-header-row">
                  <div class="status-header">本周部位训练负荷</div>
                  <div class="status-note-inline">基于本周训练容量</div>
                </div>
                <div class="muscle-recovery-list">
                  <div v-for="muscle in volumeStatus" :key="muscle.name" class="muscle-item">
                    <span class="m-name">{{ muscle.name }}</span>
                    <el-progress :percentage="muscle.percentage" :stroke-width="10" :color="muscle.color" />
                  </div>
                </div>
              </el-card>

              <el-card shadow="hover" class="status-card trend-card" @click="router.push('/analytics')">
                <div class="status-header">📈 进度轨迹</div>
                <p class="status-desc">查看体重、围度、训练完成度等指标变化。</p>
              </el-card>
            </div>
          </el-card>
          </section>
        </el-card>

      </div>

      <aside class="right-panel">
        <AIRecommendations ref="recommendationsRef" :max-items="4" />
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import apiClient from '../api'
import AIRecommendations from '../components/AIRecommendations.vue'

const router = useRouter()
const username = ref(localStorage.getItem('username') || '健身者')
const loading = ref(false)
const growthLoading = ref(false)
const stats = ref<any>({})
const userStatus = ref<any>(null)
const recommendationsRef = ref<any>(null)
const profile = ref<any>(null)
const showWelcomeBanner = ref(true)
let welcomeTimer: number | null = null

// 调试开关：
// true  -> 每次进入首页都播放欢迎横幅（便于调试动画）
// false -> 仅首次进入显示一次，后续不再出现
const FORCE_REPEAT_WELCOME_BANNER = false
const WELCOME_BANNER_SEEN_KEY = 'fitvision_home_welcome_seen'

// 米兰色系（低饱和、高质感）
const MILAN_COLORS = {
  pageBase: '#F5F2ED', // 页面大背景 / 卡片背景
  surface: '#E5E0D8', // 悬浮层 / 输入区背景 / 弱对比边框
  surfaceMid: '#DCCFBE', // 低中进度条 / 轻强调底色
  textPrimary: '#3C2F2F', // 标题 / 正文主文字
  textSecondary: '#7D756D', // 注释 / 辅助信息
  accent: '#BEA47E', // 按钮 / 选中状态 / 重点进度
  accentSoft: '#D5C6B0', // 次级点缀 / 中段进度
  accentDeep: '#9F8462', // 深层强调 / 渐变深色端
}

const userStats = ref<any>({})

const growth = ref({
  weeklyTrainingDays: 0,
  currentStreak: 0,
  bestWeeklyExercise: '继续训练解锁',
  bestWeeklyImprovementText: '完成训练后自动计算进步幅度',
  positiveMessage: '每次打开都在向更好的自己靠近',
  achievements: [
    { key: 'first_training', title: '完成首训', description: '完成 1 次训练', unlocked: false },
    { key: 'streak_3', title: '连续 3 天', description: '连续打卡 3 天', unlocked: false },
    { key: 'week_3', title: '稳定习惯', description: '本周训练达到 3 天', unlocked: false },
    { key: 'improve_action', title: '动作进步', description: '本周至少 1 个动作明显进步', unlocked: false },
  ] as Array<{ key: string; title: string; description: string; unlocked: boolean }>,
})

const calorieGoal = computed(() => {
  if (!profile.value?.bmr) return 500
  // 建议目标为 BMR 的 25% 左右作为额外训练消耗
  return Math.round(profile.value.bmr * 0.3)
})

// 新增：容量达标颜色逻辑（练得越好越绿，缺乏锻炼标红）
const getVolumeColor = (percentage: number) => {
  if (percentage >= 80) return MILAN_COLORS.accent // 本周负荷高：重点色
  if (percentage >= 40) return MILAN_COLORS.accentSoft // 本周负荷中：次级点缀
  return MILAN_COLORS.surface // 本周负荷低：弱强调背景色
}

// 修改：变量名更替，并套用动态颜色函数
const volumeStatus = ref([
  { name: '胸部', percentage: 85, color: getVolumeColor(85) },
  { name: '腿部', percentage: 30, color: getVolumeColor(30) },
  { name: '核心', percentage: 60, color: getVolumeColor(60) }
])

const customColors = [
  { color: MILAN_COLORS.surface, percentage: 20 }, // 低进度：浅米灰
  { color: MILAN_COLORS.surfaceMid, percentage: 40 }, // 低中进度：浅暖米色
  { color: MILAN_COLORS.accentSoft, percentage: 60 }, // 中进度：柔和金棕
  { color: MILAN_COLORS.accent, percentage: 80 }, // 高进度：米兰主点缀
  { color: MILAN_COLORS.accentDeep, percentage: 100 }, // 满进度：深金棕强调
]

const getBMIType = (bmi: number) => {
  if (bmi < 18.5) return 'warning'
  if (bmi < 24) return 'success'
  if (bmi < 28) return 'warning'
  return 'danger'
}

const getBMIText = (bmi: number) => {
  if (bmi < 18.5) return '偏瘦'
  if (bmi < 24) return '标准'
  if (bmi < 28) return '微胖'
  return '肥胖'
}

const fetchProfile = async () => {
  try {
    const res = await apiClient.get('/auth/profile/')
    profile.value = res.data
  } catch (err) {
    console.error('Failed to fetch profile:', err)
  }
}

const scrollToRecs = (targetScenario?: string) => {
  recommendationsRef.value?.$el.scrollIntoView({ behavior: 'smooth' })
  const finalScenario = targetScenario || (userStatus.value?.fatigue_level > 0.7 ? 'auto_adjust' : null)
  if (finalScenario) {
    recommendationsRef.value?.setScenario(finalScenario)
  }
}

const fetchUserStatus = async () => {
  try {
    const res = await apiClient.get('/recommendations/list/user_status/')
    userStatus.value = res.data
    // 修改：如果后端传来了 volume_stats，动态计算并赋值颜色
    if (res.data.volume_stats) {
      volumeStatus.value = res.data.volume_stats.map((item: any) => ({
        ...item,
        color: getVolumeColor(item.percentage)
      }))
    }
  } catch (err) {
    console.error('Failed to fetch user status:', err)
  }
}

const fetchTodayStats = async () => {
  loading.value = true
  try {
    const res = await apiClient.get('/analytics/daily-stats/today/')
    stats.value = res.data
  } catch (err) {
    console.error('Failed to fetch today stats:', err)
  } finally {
    loading.value = false
  }
}

const dateToKey = (date: Date) => {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

const shiftDays = (date: Date, delta: number) => {
  const next = new Date(date)
  next.setDate(next.getDate() + delta)
  return next
}

const computeCurrentStreak = (trainedDateKeys: Set<string>) => {
  if (trainedDateKeys.size === 0) return 0

  const today = new Date()
  let cursor = new Date(today)

  if (!trainedDateKeys.has(dateToKey(cursor))) {
    cursor = shiftDays(cursor, -1)
  }

  let streak = 0
  while (trainedDateKeys.has(dateToKey(cursor))) {
    streak += 1
    cursor = shiftDays(cursor, -1)
  }
  return streak
}

const isTrainingDay = (item: any) => {
  return (item?.total_duration_minutes || 0) > 0 ||
    (item?.completed_sessions || 0) > 0 ||
    (item?.completed_exercises || 0) > 0
}

const evaluateBestWeeklyExercise = (items: any[]) => {
  if (!items?.length) {
    return { name: '继续训练解锁', text: '完成训练后自动计算进步幅度', improved: false }
  }

  const start = shiftDays(new Date(), -6)
  const startKey = dateToKey(start)
  const grouped = new Map<number, any[]>()

  for (const item of items) {
    const id = Number(item.exercise) || Number(item.exercise_id)
    if (!id) continue
    const list = grouped.get(id) || []
    list.push(item)
    grouped.set(id, list)
  }

  let best: { name: string; score: number } | null = null
  for (const records of grouped.values()) {
    records.sort((a, b) => String(a.date).localeCompare(String(b.date)))
    const thisWeek = records.filter((r) => String(r.date) >= startKey)
    if (thisWeek.length === 0) continue

    const latest = thisWeek[thisWeek.length - 1]
    const previous = records.filter((r) => String(r.date) < startKey).slice(-1)[0]

    const scoreDelta = (Number(latest.best_form_score) || 0) - (Number(previous?.best_form_score) || 0)
    const volPrev = Number(previous?.total_volume) || 0
    const volNow = Number(latest.total_volume) || 0
    const volDeltaRatio = volPrev > 0 ? (volNow - volPrev) / volPrev : (volNow > 0 ? 0.2 : 0)
    const repDelta = (Number(latest.max_reps) || 0) - (Number(previous?.max_reps) || 0)
    const totalGain = scoreDelta * 1.2 + volDeltaRatio * 30 + repDelta * 1.8

    if (!best || totalGain > best.score) {
      best = {
        name: latest.exercise_name || '未命名动作',
        score: totalGain,
      }
    }
  }

  if (!best || best.score <= 0) {
    return { name: '继续训练解锁', text: '再完成几次训练即可看到明显进步', improved: false }
  }
  return {
    name: best.name,
    text: `综合进步 +${best.score.toFixed(1)}（动作质量/训练量）`,
    improved: true,
  }
}

const updateAchievements = (weeklyTrainingDays: number, currentStreak: number, improved: boolean) => {
  const totalTrainings = Number(userStats.value?.total_trainings || 0)
  growth.value.achievements = growth.value.achievements.map((item) => {
    if (item.key === 'first_training') return { ...item, unlocked: totalTrainings >= 1 }
    if (item.key === 'streak_3') return { ...item, unlocked: currentStreak >= 3 }
    if (item.key === 'week_3') return { ...item, unlocked: weeklyTrainingDays >= 3 }
    if (item.key === 'improve_action') return { ...item, unlocked: improved }
    return item
  })

  if (currentStreak >= 3) {
    growth.value.positiveMessage = `太棒了，已连续打卡 ${currentStreak} 天！`
  } else if (weeklyTrainingDays >= 3) {
    growth.value.positiveMessage = `本周已训练 ${weeklyTrainingDays} 天，状态很稳！`
  } else if (totalTrainings >= 1) {
    growth.value.positiveMessage = '训练习惯正在形成，今天继续打卡吧！'
  } else {
    growth.value.positiveMessage = '完成首训就能点亮第一枚成就！'
  }
}

const fetchGrowthData = async () => {
  growthLoading.value = true
  try {
    const [summaryRes, userStatsRes, progressRes] = await Promise.all([
      apiClient.get('/analytics/daily-stats/summary/?days=30'),
      apiClient.get('/auth/stats/'),
      apiClient.get('/analytics/exercise-progress/'),
    ])

    userStats.value = userStatsRes.data || {}
    const dailyStats = summaryRes.data?.daily_breakdown || []
    const progressItems = progressRes.data || []

    const trainedKeys: Set<string> = new Set(
      dailyStats
        .filter((item: any) => isTrainingDay(item))
        .map((item: any) => String(item.date))
    )

    const weekStart = dateToKey(shiftDays(new Date(), -6))
    const weeklyTrainingDays = dailyStats.filter((item: any) => String(item.date) >= weekStart && isTrainingDay(item)).length
    const currentStreak = computeCurrentStreak(trainedKeys)
    const bestProgress = evaluateBestWeeklyExercise(progressItems)

    growth.value.weeklyTrainingDays = weeklyTrainingDays
    growth.value.currentStreak = currentStreak
    growth.value.bestWeeklyExercise = bestProgress.name
    growth.value.bestWeeklyImprovementText = bestProgress.text

    updateAchievements(weeklyTrainingDays, currentStreak, bestProgress.improved)
  } catch (err) {
    console.error('Failed to fetch growth data:', err)
  } finally {
    growthLoading.value = false
  }
}

onMounted(() => {
  const hasSeenWelcomeBanner = localStorage.getItem(WELCOME_BANNER_SEEN_KEY) === '1'

  // 非调试模式且已经展示过：直接不显示横幅
  if (!FORCE_REPEAT_WELCOME_BANNER && hasSeenWelcomeBanner) {
    showWelcomeBanner.value = false
  } else {
    // 首次（或调试模式）展示 5 秒后淡出并记录已展示
    welcomeTimer = window.setTimeout(() => {
      showWelcomeBanner.value = false
      if (!FORCE_REPEAT_WELCOME_BANNER) {
        localStorage.setItem(WELCOME_BANNER_SEEN_KEY, '1')
      }
    }, 5000)
  }

  fetchTodayStats()
  fetchUserStatus()
  fetchProfile()
  fetchGrowthData()
})

onUnmounted(() => {
  if (welcomeTimer) {
    clearTimeout(welcomeTimer)
  }
})
</script>

<style scoped>
.dashboard-container {
  --milan-page-bg: #EEE6DB; /* 页面背景基底（比卡片更深，形成层次） */
  --milan-page-bg-soft: #E4D8C8; /* 页面背景过渡色 */
  --milan-bg-main: #FBF8F3; /* 主卡片底色（比页面更亮） */
  --milan-bg-surface: #E5E0D8; /* 浮层背景 / 弱对比边框 */
  --milan-bg-soft-contrast: #DCCFBE; /* 次级底色 / 低中进度衔接 */
  --milan-text-primary: #3C2F2F; /* 标题 / 正文主文字 */
  --milan-text-secondary: #7D756D; /* 注释 / 时间戳 / 辅助文字 */
  --milan-accent: #BEA47E; /* 按钮 / 选中状态 / 强调色 */
  --milan-accent-soft: #D5C6B0; /* 悬浮弱强调 / 次级高亮 */
  --milan-accent-deep: #9F8462; /* 渐变深色端 / 高权重强调 */
  --milan-on-accent: #F5F2ED; /* 强调色上的文字 */
  --milan-shadow-soft: rgba(60, 47, 47, 0.12); /* 常规浮层阴影 */
  --milan-shadow-medium: rgba(60, 47, 47, 0.14); /* 中等悬浮阴影 */
  --milan-shadow-accent: rgba(190, 164, 126, 0.24); /* 强调态阴影 */

  background:
    radial-gradient(1200px 400px at 10% -10%, rgba(245, 242, 237, 0.65), transparent 55%),
    radial-gradient(1000px 360px at 95% 0%, rgba(213, 198, 176, 0.22), transparent 58%),
    linear-gradient(180deg, var(--milan-page-bg) 0%, var(--milan-page-bg-soft) 100%);
  color: var(--milan-text-primary);
  border-radius: 12px;
  padding: 8px;
  padding-bottom: 12px;
}

.welcome-banner {
  background: linear-gradient(135deg, var(--milan-accent) 0%, var(--milan-accent-deep) 100%);
  border-radius: 12px;
  padding: 18px 22px;
  color: var(--milan-on-accent);
  margin-bottom: 14px;
  box-shadow: 0 6px 14px var(--milan-shadow-soft);
}

.banner-content h1 {
  font-size: 24px;
  margin-bottom: 4px;
}

.banner-collapse-enter-active,
.banner-collapse-leave-active {
  transition: all 0.32s ease;
  overflow: hidden;
}

.banner-collapse-enter-from,
.banner-collapse-leave-to {
  opacity: 0;
  transform: translateY(-8px);
  max-height: 0;
  margin-bottom: 0;
  padding-top: 0;
  padding-bottom: 0;
}

.banner-content p {
  font-size: 14px;
  opacity: 0.9;
  margin-bottom: 0;
}

.section {
  margin-bottom: 12px;
}

.left-overview-shell {
  border: 1px solid var(--milan-bg-surface);
  border-radius: 12px;
  height: 100%;
  width: 100%;
  background: var(--milan-bg-main);
}

.left-overview-shell :deep(.el-card__body) {
  padding: 10px;
}

.left-overview-shell .section {
  margin-bottom: 0;
}

.right-panel :deep(.recommendation-section) {
  width: 100%;
  height: 100%;
}

.right-panel :deep(.recommendation-section .el-card__body) {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.module-shell {
  border: 1px solid var(--milan-bg-surface);
  background: var(--milan-bg-main);
}

.module-shell :deep(.el-card__header) {
  padding: 10px 12px;
}

.module-shell :deep(.el-card__body) {
  padding: 12px;
}

.module-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(320px, 1fr);
  gap: 10px;
  align-items: stretch;
}

.left-panel,
.right-panel {
  min-width: 0;
  display: flex;
}

.training-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.growth-section {
  margin-top: 0;
  display: grid;
  grid-template-columns: minmax(0, 0.42fr) minmax(0, 0.58fr);
  gap: 8px;
}

.growth-header {
  grid-column: 1 / -1;
  justify-content: space-between;
}

.growth-cards {
  grid-column: 1 / -1;
  margin-bottom: 8px;
}

.growth-card {
  border-radius: 10px;
  border: 1px solid var(--milan-bg-surface);
  background: var(--milan-bg-main);
}

.growth-card :deep(.el-card__body) {
  padding: 9px;
}

.growth-action-card {
  cursor: default;
}

.growth-action-card:hover {
  border-color: var(--milan-accent);
  box-shadow: 0 6px 14px var(--milan-shadow-accent);
}

.growth-action-buttons {
  display: flex;
  gap: 6px;
  margin-top: 6px;
}

.growth-action-buttons .el-button {
  flex: 1;
}

.growth-card-title {
  color: var(--milan-text-secondary);
  font-size: 12px;
  margin-bottom: 6px;
}

.growth-card-value {
  color: var(--milan-text-primary);
  font-size: 24px;
  font-weight: 800;
  margin-bottom: 4px;
}

.growth-card-value span {
  font-size: 12px;
  font-weight: 500;
  color: var(--milan-text-secondary);
}

.growth-action {
  font-size: 17px;
  line-height: 1.2;
}

.growth-card-sub {
  color: var(--milan-text-secondary);
  font-size: 11px;
}

.achievement-card {
  border-radius: 10px;
  border: 1px dashed var(--milan-accent-soft);
  background: var(--milan-bg-main);
  width: 100%;
  max-width: none;
  margin: 0;
}

.achievement-card :deep(.el-card__body) {
  padding: 9px;
}

.compact-status-shell {
  width: 100%;
}

.compact-status-shell :deep(.el-card__header) {
  padding: 8px 10px;
}

.compact-status-shell :deep(.el-card__body) {
  padding: 8px;
}

.status-inline-four {
  grid-template-columns: 1fr;
  gap: 6px;
}

.compact-status-shell .status-header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 4px;
}

.compact-status-shell .status-note-inline {
  font-size: 9px;
  color: var(--milan-text-secondary);
  text-align: right;
  line-height: 1.25;
  max-width: 56%;
}

.compact-status-shell .status-header {
  font-size: 10px;
  margin-bottom: 0;
}

.compact-status-shell .status-inline-value {
  font-size: 15px;
  font-weight: 700;
  color: var(--milan-text-primary);
  margin-left: 6px;
  line-height: 1;
}

.compact-status-shell .status-inline-value span {
  font-size: 9px;
  font-weight: 500;
  color: var(--milan-text-secondary);
}

.compact-status-shell .status-value {
  font-size: 16px;
  margin-bottom: 4px;
}

.compact-status-shell .status-value span {
  font-size: 11px;
}

.compact-status-shell .status-desc {
  font-size: 10px;
  margin: 3px 0 4px;
}

.compact-status-shell .m-name {
  font-size: 10px;
}

.achievement-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--milan-text-primary);
  margin-bottom: 6px;
}

.achievement-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.achievement-item {
  display: flex;
  gap: 8px;
  align-items: center;
}

.achievement-content {
  display: flex;
  flex-direction: column;
}

.achievement-name {
  font-size: 12px;
  color: var(--milan-text-primary);
  font-weight: 600;
}

.achievement-desc {
  font-size: 11px;
  color: var(--milan-text-secondary);
}

.section-title {
  font-size: 18px;
  font-weight: bold;
  margin: 0;
  color: var(--milan-text-primary);
}

.feature-card {
  height: 100%;
  cursor: pointer;
  transition: all 0.3s;
  text-align: center;
  padding: 2px;
}

.feature-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 16px var(--milan-shadow-medium);
  border-color: var(--milan-accent);
}

.feature-card.compact {
  padding: 2px;
}

.feature-card.compact :deep(.el-card__body) {
  padding: 10px;
}

.card-icon {
  font-size: 22px;
  margin-bottom: 6px;
}

.feature-card h3 {
  margin: 4px 0;
  font-size: 14px;
}

.feature-card p {
  font-size: 12px;
  color: var(--milan-text-secondary);
  margin: 0;
}

.status-card {
  height: 100%;
}

.status-card :deep(.el-card__body) {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 8px;
}

.status-header {
  font-size: 12px;
  color: var(--milan-text-secondary);
  margin-bottom: 6px;
}

.status-value {
  font-size: 22px;
  font-weight: bold;
  color: var(--milan-text-primary);
  margin-bottom: 8px;
}

.status-value span {
  font-size: 12px;
  font-weight: normal;
  color: var(--milan-text-secondary);
}

.status-desc {
  margin: 6px 0 8px;
  font-size: 12px;
  color: var(--milan-text-secondary);
  line-height: 1.35;
  flex: 0;
}

.trend-card :deep(.el-card__body) {
  justify-content: flex-start;
}

.trend-card .status-desc {
  margin: 4px 0 6px;
}

.trend-card .el-button {
  margin-top: 0;
  padding-top: 0;
  padding-bottom: 0;
  align-self: flex-start;
}

.section-header {
  gap: 10px;
}

.muscle-recovery-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 6px 0;
}

.muscle-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.m-name {
  font-size: 12px;
  color: var(--milan-text-secondary);
  min-width: 40px;
}

.muscle-item :deep(.el-progress) {
  flex: 1;
}

.status-footer {
  margin-top: 6px;
  font-size: 11px;
  color: var(--milan-text-secondary);
}

.dashboard-container :deep(.el-button--primary) {
  --el-button-bg-color: var(--milan-accent);
  --el-button-border-color: var(--milan-accent);
  --el-button-hover-bg-color: var(--milan-accent-deep);
  --el-button-hover-border-color: var(--milan-accent-deep);
  --el-button-active-bg-color: var(--milan-accent-deep);
  --el-button-active-border-color: var(--milan-accent-deep);
  --el-button-text-color: var(--milan-on-accent);
}

.dashboard-container :deep(.el-button--default) {
  --el-button-border-color: var(--milan-bg-surface);
  --el-button-hover-border-color: var(--milan-accent-soft);
  --el-button-hover-text-color: var(--milan-accent-deep);
}

.dashboard-container :deep(.el-progress-bar__outer) {
  background: var(--milan-bg-soft-contrast);
}

@media (max-width: 1200px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
    align-items: start;
  }

  .growth-section {
    grid-template-columns: 1fr;
  }

  .status-inline-four {
    grid-template-columns: 1fr;
  }

  .left-panel,
  .right-panel {
    display: block;
  }

  .left-overview-shell,
  .right-panel :deep(.recommendation-section) {
    height: auto;
  }
}

@media (max-width: 900px) {
  .training-grid,
  .status-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .welcome-banner {
    padding: 14px 16px;
  }

  .achievement-card {
    width: 100%;
    max-width: none;
  }
}
</style>
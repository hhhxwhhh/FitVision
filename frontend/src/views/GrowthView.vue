<template>
  <div class="growth-page" v-loading="loading">
    <header class="growth-hero">
      <div class="level-card">
        <div class="level-ring" role="img" :aria-label="`当前等级 ${progressInfo.level}`">
          <svg viewBox="0 0 120 120">
            <circle class="ring-track" cx="60" cy="60" r="48" />
            <circle
              class="ring-value"
              cx="60"
              cy="60"
              r="48"
              :stroke-dasharray="`${progressInfo.progress_percent * 3.016} 301.6`"
            />
          </svg>
          <div class="ring-center">
            <small>Lv.</small>
            <strong>{{ progressInfo.level }}</strong>
          </div>
        </div>

        <div class="level-copy">
          <span class="eyebrow">成长等级</span>
          <h1>{{ progressInfo.title }}训练者</h1>
          <p>{{ levelHint }}</p>
          <div class="xp-bar">
            <span :style="{ width: `${progressInfo.progress_percent}%` }"></span>
          </div>
          <div class="xp-meta">
            <span>{{ progressInfo.xp_into_level }} / {{ progressInfo.level_span }} XP</span>
            <span>距离下一级还差 {{ progressInfo.xp_next_level }} XP</span>
          </div>
        </div>
      </div>

      <div class="hero-stats">
        <article>
          <span class="stat-icon streak"><el-icon><TrendCharts /></el-icon></span>
          <div>
            <small>当前连续</small>
            <strong>{{ progressInfo.current_streak }}<em>天</em></strong>
          </div>
        </article>
        <article>
          <span class="stat-icon best"><el-icon><Trophy /></el-icon></span>
          <div>
            <small>最长连续</small>
            <strong>{{ progressInfo.longest_streak }}<em>天</em></strong>
          </div>
        </article>
        <article>
          <span class="stat-icon sessions"><el-icon><VideoPlay /></el-icon></span>
          <div>
            <small>累计训练</small>
            <strong>{{ progressInfo.total_sessions }}<em>次</em></strong>
          </div>
        </article>
        <article>
          <span class="stat-icon records"><el-icon><Medal /></el-icon></span>
          <div>
            <small>个人纪录</small>
            <strong>{{ records.length }}<em>项</em></strong>
          </div>
        </article>
      </div>

      <div class="readiness-chip" :class="`tone-${readiness.tone}`">
        <div class="readiness-score">{{ readiness.score }}</div>
        <div>
          <strong>{{ readiness.label }}</strong>
          <p>{{ readiness.advice }}</p>
        </div>
      </div>
    </header>

    <div class="growth-grid">
      <div class="growth-main">
        <section class="panel">
          <div class="panel-head">
            <div>
              <h2>每日任务</h2>
              <p>每天 0 点刷新，完成后领取经验</p>
            </div>
            <span class="panel-badge">{{ claimedCount }}/{{ quests.length }} 已领取</span>
          </div>

          <div class="quest-list">
            <article
              v-for="quest in quests"
              :key="quest.id"
              class="quest"
              :class="{ done: quest.is_completed, claimed: quest.is_claimed }"
            >
              <span class="quest-icon">
                <el-icon><Check v-if="quest.is_claimed" /><Aim v-else /></el-icon>
              </span>
              <div class="quest-body">
                <div class="quest-title">
                  <strong>{{ quest.title }}</strong>
                  <span class="quest-xp">+{{ quest.xp_reward }} XP</span>
                </div>
                <p>{{ quest.description }}</p>
                <div class="quest-progress">
                  <div class="bar"><span :style="{ width: `${quest.progress_percent}%` }"></span></div>
                  <small>{{ formatNumber(quest.progress) }} / {{ formatNumber(quest.target) }}</small>
                </div>
              </div>
              <el-button
                v-if="!quest.is_claimed"
                size="small"
                :type="quest.is_completed ? 'primary' : 'default'"
                :disabled="!quest.is_completed"
                :loading="claimingQuest === quest.id"
                @click="claimQuest(quest.id)"
              >
                {{ quest.is_completed ? '领取' : '进行中' }}
              </el-button>
              <el-tag v-else size="small" type="success" effect="plain">已领取</el-tag>
            </article>
          </div>
        </section>

        <section class="panel challenge-panel">
          <div class="panel-head">
            <div>
              <h2>限时挑战</h2>
              <p>周挑战每周一刷新，月挑战每月 1 日刷新</p>
            </div>
            <span class="panel-badge">{{ challengeSummary }}</span>
          </div>

          <div class="challenge-grid">
            <article
              v-for="challenge in challenges"
              :key="challenge.id"
              class="challenge-card"
              :class="{ joined: challenge.is_joined, done: challenge.is_claimed }"
            >
              <div class="challenge-head">
                <span class="challenge-icon">
                  <el-icon><component :is="iconFor(challenge.icon)" /></el-icon>
                </span>
                <div class="challenge-title">
                  <strong>{{ challenge.title }}</strong>
                  <small>{{ challenge.period_label }} · 截止 {{ dateLabel(challenge.period_end) }}</small>
                </div>
                <span class="challenge-xp">+{{ challenge.xp_reward }} XP</span>
              </div>

              <p class="challenge-desc">{{ challenge.description }}</p>

              <div class="challenge-progress">
                <div class="bar"><span :style="{ width: `${challenge.progress_percent}%` }"></span></div>
                <small>
                  {{ formatNumber(challenge.progress) }} / {{ formatNumber(challenge.target) }}
                  {{ challenge.metric_label }}
                </small>
              </div>

              <div class="challenge-actions">
                <el-tag v-if="challenge.is_claimed" type="success" effect="plain" size="small">
                  已完成
                </el-tag>
                <el-button
                  v-else-if="!challenge.is_joined"
                  size="small"
                  :loading="joiningChallenge === challenge.id"
                  @click="joinChallenge(challenge.id)"
                >
                  参加挑战
                </el-button>
                <el-button
                  v-else
                  size="small"
                  :type="challenge.can_claim ? 'primary' : 'default'"
                  :disabled="!challenge.can_claim"
                  :loading="claimingChallenge === challenge.id"
                  @click="claimChallenge(challenge.id)"
                >
                  {{
                    challenge.can_claim
                      ? `领取 ${challenge.xp_reward} XP`
                      : challenge.is_completed
                        ? '领取'
                        : '进行中'
                  }}
                </el-button>
              </div>
            </article>
          </div>

          <el-empty
            v-if="challenges.length === 0"
            description="暂时没有开放的挑战"
            :image-size="90"
          />
        </section>

        <section class="panel achievements-panel">
          <div class="panel-head">
            <div>
              <h2>成就墙</h2>
              <p>解锁 {{ unlockedAchievements }}/{{ achievements.length }} 项成就</p>
            </div>
            <div class="filter-chips">
              <button
                v-for="category in categories"
                :key="category.value"
                type="button"
                class="filter-chip"
                :class="{ active: activeCategory === category.value }"
                @click="activeCategory = category.value"
              >
                {{ category.label }}
              </button>
            </div>
          </div>

          <div class="achievement-grid">
            <article
              v-for="item in filteredAchievements"
              :key="item.id"
              class="achievement"
              :class="{ unlocked: item.unlocked }"
            >
              <span class="achievement-icon">
                <el-icon><component :is="iconFor(item.icon)" /></el-icon>
              </span>
              <div class="achievement-body">
                <div class="achievement-title">
                  <strong>{{ item.title }}</strong>
                  <span>+{{ item.xp_reward }} XP</span>
                </div>
                <p>{{ item.description }}</p>
                <div class="achievement-progress">
                  <div class="bar"><span :style="{ width: `${item.progress_percent}%` }"></span></div>
                  <small v-if="item.unlocked">已解锁</small>
                  <small v-else>{{ formatNumber(item.progress_value) }} / {{ formatNumber(item.threshold) }}</small>
                </div>
              </div>
              <span class="lock-state">
                <el-icon><Check v-if="item.unlocked" /><Lock v-else /></el-icon>
              </span>
            </article>
          </div>

          <el-empty v-if="filteredAchievements.length === 0" description="这个分类还没有成就" :image-size="90" />
        </section>
      </div>

      <aside class="growth-side">
        <section class="panel">
          <div class="panel-head">
            <div>
              <h2>本周目标</h2>
              <p>{{ weekRange }}</p>
            </div>
            <el-button text :icon="Edit" @click="editingGoal = !editingGoal">
              {{ editingGoal ? '取消' : '调整' }}
            </el-button>
          </div>

          <div v-if="editingGoal" class="goal-editor">
            <label>
              <span>训练天数</span>
              <el-input-number v-model="goalForm.target_sessions" :min="1" :max="7" size="small" />
            </label>
            <label>
              <span>训练分钟</span>
              <el-input-number v-model="goalForm.target_minutes" :min="0" :max="3000" :step="15" size="small" />
            </label>
            <el-button type="primary" :loading="savingGoal" @click="saveGoal">保存目标</el-button>
          </div>

          <div class="goal-metric">
            <div class="goal-metric-head">
              <span>训练天数</span>
              <strong>{{ weeklyGoal.completed_days }} / {{ weeklyGoal.target_sessions }}</strong>
            </div>
            <div class="bar"><span :style="{ width: `${weeklyGoal.days_percent}%` }"></span></div>
          </div>

          <div class="goal-metric">
            <div class="goal-metric-head">
              <span>训练时长</span>
              <strong>{{ weeklyGoal.completed_minutes }} / {{ weeklyGoal.target_minutes }} 分钟</strong>
            </div>
            <div class="bar"><span :style="{ width: `${weeklyGoal.minutes_percent}%` }"></span></div>
          </div>

          <el-button
            type="primary"
            class="goal-claim"
            :disabled="!weeklyGoal.can_claim"
            :loading="claimingGoal"
            @click="claimWeeklyGoal"
          >
            {{ weeklyGoal.reward_claimed ? '本周奖励已领取' : weeklyGoal.can_claim ? '领取 80 XP' : '完成目标后可领取' }}
          </el-button>
        </section>

        <section class="panel">
          <div class="panel-head">
            <div>
              <h2>本周经验榜</h2>
              <p>共 {{ leaderboard.total_participants }} 位训练者参与</p>
            </div>
            <el-switch
              v-model="isPublic"
              size="small"
              inline-prompt
              active-text="公开"
              inactive-text="隐身"
              @change="togglePublic"
            />
          </div>

          <div class="leaderboard">
            <div
              v-for="entry in leaderboard.entries"
              :key="`${entry.rank}-${entry.display_name}`"
              class="leader-row"
              :class="{ me: entry.is_me }"
            >
              <span class="rank" :class="`rank-${entry.rank}`">{{ entry.rank }}</span>
              <div class="leader-copy">
                <strong>{{ entry.display_name }}</strong>
                <small>Lv.{{ entry.level }} · {{ entry.level_title }}</small>
              </div>
              <span class="leader-xp">{{ entry.weekly_xp }} XP</span>
            </div>
            <el-empty v-if="leaderboard.entries.length === 0" description="本周还没有上榜记录" :image-size="80" />
          </div>
        </section>

        <section class="panel">
          <div class="panel-head">
            <div>
              <h2>个人纪录</h2>
              <p>最近刷新的最佳表现</p>
            </div>
            <el-icon class="head-icon"><Histogram /></el-icon>
          </div>

          <div class="record-list">
            <div v-for="record in records" :key="record.id" class="record-row">
              <div>
                <strong>{{ record.exercise_name }}</strong>
                <small>{{ record.record_type_label }}</small>
              </div>
              <span class="record-value">{{ formatRecord(record) }}</span>
            </div>
            <el-empty v-if="records.length === 0" description="完成一次训练后生成个人纪录" :image-size="80" />
          </div>
        </section>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, type Component } from 'vue'
import {
  Aim,
  Calendar,
  Check,
  Clock,
  Compass,
  DataLine,
  Edit,
  Histogram,
  HotWater,
  Lock,
  Medal,
  Moon,
  Star,
  Sunrise,
  TrendCharts,
  Trophy,
  VideoPlay,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import apiClient from '../api'

interface ProgressInfo {
  level: number
  title: string
  xp: number
  xp_into_level: number
  xp_next_level: number
  level_span: number
  progress_percent: number
  current_streak: number
  longest_streak: number
  total_sessions: number
  is_public: boolean
}

interface Quest {
  id: number
  title: string
  description: string
  metric: string
  target: number
  progress: number
  xp_reward: number
  is_completed: boolean
  is_claimed: boolean
  progress_percent: number
}

interface Challenge {
  id: number
  code: string
  title: string
  description: string
  period: string
  period_label: string
  metric_label: string
  target: number
  xp_reward: number
  icon: string
  period_start: string
  period_end: string
  progress: number
  progress_percent: number
  is_joined: boolean
  is_completed: boolean
  is_claimed: boolean
  can_claim: boolean
}

interface WeeklyGoal {
  target_sessions: number
  target_minutes: number
  completed_days: number
  completed_minutes: number
  days_percent: number
  minutes_percent: number
  can_claim: boolean
  reward_claimed: boolean
  week_start: string
}

interface AchievementItem {
  id: number
  code: string
  title: string
  description: string
  category: string
  icon: string
  xp_reward: number
  threshold: number
  unlocked: boolean
  progress_value: number
  progress_percent: number
}

interface PersonalRecord {
  id: number
  exercise_name: string
  record_type: string
  record_type_label: string
  value: number
}

interface LeaderEntry {
  rank: number
  display_name: string
  weekly_xp: number
  level: number
  level_title: string
  is_me: boolean
}

interface Leaderboard {
  entries: LeaderEntry[]
  me: LeaderEntry | null
  total_participants: number
}

const loading = ref(false)
const claimingQuest = ref<number | null>(null)
const claimingChallenge = ref<number | null>(null)
const joiningChallenge = ref<number | null>(null)
const claimingGoal = ref(false)
const savingGoal = ref(false)
const editingGoal = ref(false)
const activeCategory = ref('all')
const isPublic = ref(true)

const progressInfo = ref<ProgressInfo>({
  level: 1,
  title: '新手',
  xp: 0,
  xp_into_level: 0,
  xp_next_level: 100,
  level_span: 100,
  progress_percent: 0,
  current_streak: 0,
  longest_streak: 0,
  total_sessions: 0,
  is_public: true,
})

const readiness = ref({
  score: 60,
  tone: 'good',
  label: '适合训练',
  advice: '完成一次训练后，这里会给出更准确的建议。',
})

const quests = ref<Quest[]>([])
const challenges = ref<Challenge[]>([])
const achievements = ref<AchievementItem[]>([])
const records = ref<PersonalRecord[]>([])
const weeklyGoal = ref<WeeklyGoal>({
  target_sessions: 3,
  target_minutes: 150,
  completed_days: 0,
  completed_minutes: 0,
  days_percent: 0,
  minutes_percent: 0,
  can_claim: false,
  reward_claimed: false,
  week_start: '',
})
const leaderboard = ref<Leaderboard>({ entries: [], me: null, total_participants: 0 })
const goalForm = reactive({ target_sessions: 3, target_minutes: 150 })

const iconMap: Record<string, Component> = {
  Trophy,
  Medal,
  Star,
  Aim,
  Clock,
  HotWater,
  TrendCharts,
  DataLine,
  Compass,
  Calendar,
  Sunrise,
  Moon,
}

const categories = [
  { value: 'all', label: '全部' },
  { value: 'milestone', label: '里程碑' },
  { value: 'streak', label: '连续性' },
  { value: 'volume', label: '训练量' },
  { value: 'quality', label: '动作质量' },
  { value: 'exploration', label: '探索' },
  { value: 'special', label: '特别' },
]

const iconFor = (name: string) => iconMap[name] || Trophy

const levelHint = computed(() => {
  if (progressInfo.value.progress_percent >= 80) return '再完成一次训练，就能升到下一级。'
  if (progressInfo.value.current_streak >= 3) return '连续性正在转化为可见的成长。'
  return '每一次训练都会累积经验，保持节奏即可升级。'
})

const claimedCount = computed(() => quests.value.filter((quest) => quest.is_claimed).length)
const challengeSummary = computed(() => {
  const claimable = challenges.value.filter((item) => item.can_claim).length
  if (claimable > 0) return `${claimable} 项可领取`
  const joined = challenges.value.filter((item) => item.is_joined).length
  return `${joined}/${challenges.value.length} 已参加`
})
const unlockedAchievements = computed(
  () => achievements.value.filter((item) => item.unlocked).length,
)

const filteredAchievements = computed(() =>
  activeCategory.value === 'all'
    ? achievements.value
    : achievements.value.filter((item) => item.category === activeCategory.value),
)

const weekRange = computed(() => {
  if (!weeklyGoal.value.week_start) return ''
  const start = new Date(`${weeklyGoal.value.week_start}T00:00:00`)
  const end = new Date(start)
  end.setDate(start.getDate() + 6)
  return `${monthDay(start)} - ${monthDay(end)}`
})

function monthDay(date: Date) {
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

function dateLabel(iso: string) {
  if (!iso) return ''
  return monthDay(new Date(`${iso}T00:00:00`))
}

function formatNumber(value: number) {
  return Number.isInteger(value) ? String(value) : value.toFixed(1)
}

function formatRecord(record: PersonalRecord) {
  if (record.record_type === 'max_weight') return `${formatNumber(record.value)} kg`
  if (record.record_type === 'max_reps') return `${formatNumber(record.value)} 次`
  if (record.record_type === 'max_volume') return `${formatNumber(record.value)} kg`
  return `${formatNumber(record.value)} 分`
}

function errorMessage(error: any, fallback: string) {
  return error?.response?.data?.detail || fallback
}

async function fetchOverview() {
  const response = await apiClient.get('/growth/overview/')
  const data = response.data
  progressInfo.value = data.progress
  isPublic.value = data.progress.is_public
  readiness.value = data.readiness
  quests.value = data.daily_quests
  weeklyGoal.value = data.weekly_goal
  records.value = data.personal_records
  goalForm.target_sessions = data.weekly_goal.target_sessions
  goalForm.target_minutes = data.weekly_goal.target_minutes
}

async function fetchChallenges() {
  const response = await apiClient.get('/growth/challenges/')
  challenges.value = response.data.results
}

async function fetchAchievements() {
  const response = await apiClient.get('/growth/achievements/')
  achievements.value = response.data.results
}

async function fetchLeaderboard() {
  const response = await apiClient.get('/growth/leaderboard/?limit=10')
  leaderboard.value = response.data
}

async function loadAll() {
  loading.value = true
  try {
    await Promise.allSettled([
      fetchOverview(),
      fetchChallenges(),
      fetchAchievements(),
      fetchLeaderboard(),
    ])
  } finally {
    loading.value = false
  }
}

async function claimQuest(id: number) {
  claimingQuest.value = id
  try {
    const response = await apiClient.post(`/growth/quests/${id}/claim/`)
    ElMessage.success(`任务完成，获得 ${response.data.awarded_xp} XP`)
    await Promise.allSettled([fetchOverview(), fetchLeaderboard()])
  } catch (error: any) {
    ElMessage.error(errorMessage(error, '领取失败，请稍后再试'))
  } finally {
    claimingQuest.value = null
  }
}

async function joinChallenge(id: number) {
  joiningChallenge.value = id
  try {
    await apiClient.post(`/growth/challenges/${id}/join/`)
    ElMessage.success('已参加挑战，完成目标后记得领取奖励')
    await fetchChallenges()
  } catch (error: any) {
    ElMessage.error(errorMessage(error, '参加挑战失败，请稍后再试'))
  } finally {
    joiningChallenge.value = null
  }
}

async function claimChallenge(id: number) {
  claimingChallenge.value = id
  try {
    const response = await apiClient.post(`/growth/challenges/${id}/claim/`)
    ElMessage.success(`挑战完成，获得 ${response.data.awarded_xp} XP`)
    await Promise.allSettled([
      fetchChallenges(),
      fetchOverview(),
      fetchAchievements(),
      fetchLeaderboard(),
    ])
  } catch (error: any) {
    ElMessage.error(errorMessage(error, '领取失败，请先完成挑战'))
  } finally {
    claimingChallenge.value = null
  }
}

async function saveGoal() {
  savingGoal.value = true
  try {
    await apiClient.put('/growth/weekly-goal/', {
      target_sessions: goalForm.target_sessions,
      target_minutes: goalForm.target_minutes,
    })
    ElMessage.success('本周目标已更新')
    editingGoal.value = false
    await fetchOverview()
  } catch (error: any) {
    ElMessage.error(errorMessage(error, '目标保存失败'))
  } finally {
    savingGoal.value = false
  }
}

async function claimWeeklyGoal() {
  claimingGoal.value = true
  try {
    const response = await apiClient.post('/growth/weekly-goal/claim/')
    ElMessage.success(`本周目标达成，获得 ${response.data.awarded_xp} XP`)
    await Promise.allSettled([fetchOverview(), fetchLeaderboard()])
  } catch (error: any) {
    ElMessage.error(errorMessage(error, '领取失败，请先完成本周目标'))
  } finally {
    claimingGoal.value = false
  }
}

async function togglePublic() {
  try {
    await apiClient.put('/growth/settings/', { is_public: isPublic.value })
    await fetchLeaderboard()
  } catch (error: any) {
    isPublic.value = !isPublic.value
    ElMessage.error(errorMessage(error, '设置保存失败'))
  }
}

onMounted(loadAll)
</script>

<style scoped>
.growth-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.growth-hero {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(280px, 0.85fr);
  gap: 22px;
  padding: clamp(22px, 3vw, 34px);
  border-radius: var(--fv-radius-xl);
  border: 1px solid var(--fv-border);
  background:
    radial-gradient(620px 240px at 8% 0%, rgba(194, 65, 12, 0.12), transparent 62%),
    radial-gradient(520px 220px at 92% 100%, rgba(101, 163, 13, 0.1), transparent 60%),
    var(--fv-surface);
  box-shadow: var(--fv-shadow-md);
  overflow: hidden;
}

.level-card {
  display: flex;
  gap: 24px;
  align-items: center;
  min-width: 0;
}

.level-ring {
  position: relative;
  width: 150px;
  height: 150px;
  flex: none;
}

.level-ring svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.ring-track,
.ring-value {
  fill: none;
  stroke-width: 8;
}

.ring-track {
  stroke: var(--fv-surface-3);
}

.ring-value {
  stroke: var(--fv-primary);
  stroke-linecap: round;
  filter: none;
  transition: stroke-dasharray 0.8s cubic-bezier(0.22, 1, 0.36, 1);
}

.ring-center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--fv-text);
}

.ring-center small {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.12em;
  color: var(--fv-text-3);
}

.ring-center strong {
  font-size: 46px;
  font-weight: 900;
  letter-spacing: -0.06em;
  line-height: 1;
}

.level-copy {
  min-width: 0;
}

.eyebrow {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.14em;
  color: var(--fv-primary);
}

.level-copy h1 {
  margin: 8px 0 6px;
  font-size: clamp(24px, 3vw, 34px);
  font-weight: 900;
  letter-spacing: -0.04em;
  color: var(--fv-text);
}

.level-copy p {
  margin: 0 0 16px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--fv-text-2);
}

.xp-bar,
.goal-metric .bar,
.quest-progress .bar,
.achievement-progress .bar {
  height: 7px;
  border-radius: 999px;
  background: var(--fv-surface-3);
  overflow: hidden;
}

.xp-bar span,
.goal-metric .bar span,
.quest-progress .bar span,
.achievement-progress .bar span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--fv-accent), var(--fv-primary));
  transition: width 0.6s cubic-bezier(0.22, 1, 0.36, 1);
}

.xp-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-top: 7px;
  font-size: 11px;
  color: var(--fv-text-3);
}

.hero-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  align-content: center;
}

.hero-stats article {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 12px;
  border-radius: 14px;
  border: 1px solid var(--fv-border);
  background: var(--fv-surface-translucent);
}

.stat-icon {
  width: 34px;
  height: 34px;
  flex: none;
  display: grid;
  place-items: center;
  border-radius: 10px;
  background: var(--fv-primary-soft);
  color: var(--fv-primary);
}

.stat-icon.best {
  background: rgba(245, 158, 11, 0.14);
  color: #d97706;
}

.stat-icon.sessions {
  background: rgba(101, 163, 13, 0.1);
  color: var(--fv-accent);
}

.stat-icon.records {
  background: rgba(16, 185, 129, 0.12);
  color: var(--fv-success);
}

.hero-stats small {
  display: block;
  font-size: 10.5px;
  color: var(--fv-text-3);
}

.hero-stats strong {
  font-size: 21px;
  font-weight: 900;
  letter-spacing: -0.03em;
  color: var(--fv-text);
}

.hero-stats em {
  margin-left: 2px;
  font-style: normal;
  font-size: 10px;
  font-weight: 600;
  color: var(--fv-text-3);
}

.readiness-chip {
  grid-column: 1 / -1;
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 12px 16px;
  border-radius: 14px;
  border: 1px solid var(--fv-border);
  background: var(--fv-surface-2);
}

.readiness-score {
  width: 46px;
  height: 46px;
  flex: none;
  display: grid;
  place-items: center;
  border-radius: 50%;
  font-size: 18px;
  font-weight: 900;
  color: var(--fv-primary);
  background: var(--fv-primary-soft);
}

.readiness-chip strong {
  font-size: 13px;
  color: var(--fv-text);
}

.readiness-chip p {
  margin: 3px 0 0;
  font-size: 11.5px;
  line-height: 1.5;
  color: var(--fv-text-2);
}

.readiness-chip.tone-excellent .readiness-score {
  color: var(--fv-success);
  background: rgba(16, 185, 129, 0.12);
}

.readiness-chip.tone-moderate .readiness-score {
  color: #d97706;
  background: rgba(245, 158, 11, 0.14);
}

.readiness-chip.tone-recover .readiness-score {
  color: var(--fv-danger);
  background: rgba(239, 68, 68, 0.12);
}

.growth-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(300px, 0.8fr);
  gap: 18px;
  align-items: start;
}

.growth-main,
.growth-side {
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

.panel-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 14px;
}

.panel-head h2 {
  margin: 0;
  font-size: 17px;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: var(--fv-text);
}

.panel-head p {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--fv-text-2);
}

.panel-badge {
  flex: none;
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--fv-primary-soft);
  color: var(--fv-primary);
  font-size: 11px;
  font-weight: 800;
}

.head-icon {
  color: var(--fv-text-3);
}

.quest-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 16px;
}

.quest {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 14px;
  border-radius: 14px;
  border: 1px solid var(--fv-border);
  background: var(--fv-surface-2);
}

.quest.done {
  border-color: rgba(194, 65, 12, 0.3);
  background: var(--fv-primary-soft);
}

.quest.claimed {
  opacity: 0.62;
}

.quest-icon,
.achievement-icon {
  width: 38px;
  height: 38px;
  flex: none;
  display: grid;
  place-items: center;
  border-radius: 11px;
  background: var(--fv-surface);
  color: var(--fv-primary);
}

.quest-body {
  flex: 1;
  min-width: 0;
}

.quest-title,
.achievement-title {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: baseline;
}

.quest-title strong,
.achievement-title strong {
  font-size: 13.5px;
  color: var(--fv-text);
}

.quest-xp,
.achievement-title span {
  flex: none;
  font-size: 11px;
  font-weight: 800;
  color: var(--fv-primary);
}

.quest-body p,
.achievement-body p {
  margin: 3px 0 8px;
  font-size: 11.5px;
  color: var(--fv-text-2);
}

.quest-progress {
  display: flex;
  align-items: center;
  gap: 10px;
}

.quest-progress .bar {
  flex: 1;
  height: 5px;
}

.quest-progress small,
.achievement-progress small {
  flex: none;
  font-size: 10.5px;
  color: var(--fv-text-3);
}

.filter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  justify-content: flex-end;
}

.filter-chip {
  border: 1px solid var(--fv-border);
  background: var(--fv-surface-2);
  color: var(--fv-text-2);
  padding: 4px 9px;
  border-radius: 999px;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.filter-chip.active {
  border-color: transparent;
  background: var(--fv-primary);
  color: #fff;
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
  align-items: flex-start;
  padding: 13px;
  border-radius: 14px;
  border: 1px dashed var(--fv-border-strong);
  background: var(--fv-surface-2);
  opacity: 0.72;
}

.achievement.unlocked {
  border-style: solid;
  border-color: rgba(194, 65, 12, 0.3);
  background: var(--fv-primary-soft);
  opacity: 1;
}

.achievement.unlocked .achievement-icon {
  background: var(--fv-primary);
  color: #fff;
}

.achievement-body {
  flex: 1;
  min-width: 0;
}

.achievement-progress {
  display: flex;
  align-items: center;
  gap: 8px;
}

.achievement-progress .bar {
  flex: 1;
  height: 4px;
}

.lock-state {
  color: var(--fv-text-3);
}

.achievement.unlocked .lock-state {
  color: var(--fv-success);
}

.challenge-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 16px;
}

.challenge-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px;
  border-radius: 14px;
  border: 1px solid var(--fv-border);
  background: var(--fv-surface-2);
}

.challenge-card.joined {
  border-color: rgba(194, 65, 12, 0.28);
}

.challenge-card.done {
  opacity: 0.68;
}

.challenge-head {
  display: flex;
  gap: 10px;
  align-items: center;
}

.challenge-icon {
  width: 36px;
  height: 36px;
  flex: none;
  display: grid;
  place-items: center;
  border-radius: 11px;
  background: var(--fv-surface);
  color: var(--fv-primary);
}

.challenge-title {
  flex: 1;
  min-width: 0;
}

.challenge-title strong {
  display: block;
  font-size: 13.5px;
  color: var(--fv-text);
}

.challenge-title small {
  display: block;
  margin-top: 2px;
  font-size: 10.5px;
  color: var(--fv-text-3);
}

.challenge-xp {
  flex: none;
  font-size: 11px;
  font-weight: 800;
  color: var(--fv-primary);
}

.challenge-desc {
  margin: 0;
  min-height: 34px;
  font-size: 11.5px;
  line-height: 1.5;
  color: var(--fv-text-2);
}

.challenge-progress {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.challenge-progress .bar {
  height: 5px;
  border-radius: 999px;
  background: var(--fv-surface-3);
  overflow: hidden;
}

.challenge-progress .bar span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--fv-accent), var(--fv-primary));
  transition: width 0.6s cubic-bezier(0.22, 1, 0.36, 1);
}

.challenge-progress small {
  font-size: 10.5px;
  color: var(--fv-text-3);
}

.challenge-actions {
  display: flex;
  justify-content: flex-end;
}

.goal-editor {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 14px;
  padding: 12px;
  border-radius: 12px;
  background: var(--fv-surface-2);
}

.goal-editor label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-size: 12px;
  color: var(--fv-text-2);
}

.goal-metric {
  margin-top: 16px;
}

.goal-metric-head {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  font-size: 12px;
  color: var(--fv-text-2);
  margin-bottom: 7px;
}

.goal-metric-head strong {
  color: var(--fv-text);
}

.goal-claim {
  width: 100%;
  margin-top: 18px;
}

.leaderboard {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 12px;
}

.leader-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 10px;
}

.leader-row.me {
  background: var(--fv-primary-soft);
}

.rank {
  width: 24px;
  height: 24px;
  flex: none;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: var(--fv-surface-2);
  font-size: 11px;
  font-weight: 800;
  color: var(--fv-text-2);
}

.rank-1 {
  background: rgba(245, 158, 11, 0.16);
  color: #b45309;
}

.rank-2 {
  background: rgba(148, 163, 184, 0.2);
  color: #475569;
}

.rank-3 {
  background: rgba(180, 83, 9, 0.14);
  color: #92400e;
}

.leader-copy {
  flex: 1;
  min-width: 0;
}

.leader-copy strong {
  display: block;
  font-size: 12.5px;
  color: var(--fv-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.leader-copy small {
  display: block;
  font-size: 10.5px;
  color: var(--fv-text-3);
}

.leader-xp {
  flex: none;
  font-size: 11.5px;
  font-weight: 800;
  color: var(--fv-primary);
}

.record-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
}

.record-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 11px;
  background: var(--fv-surface-2);
}

.record-row strong {
  display: block;
  font-size: 12.5px;
  color: var(--fv-text);
}

.record-row small {
  display: block;
  font-size: 10.5px;
  color: var(--fv-text-3);
}

.record-value {
  flex: none;
  font-size: 13px;
  font-weight: 800;
  color: var(--fv-primary);
}

@media (max-width: 1100px) {
  .growth-hero,
  .growth-grid {
    grid-template-columns: 1fr;
  }

  .hero-stats {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .level-card {
    flex-direction: column;
    align-items: flex-start;
    text-align: left;
  }

  .hero-stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .achievement-grid,
  .challenge-grid {
    grid-template-columns: 1fr;
  }

  .quest {
    flex-wrap: wrap;
  }
}
</style>

<template>
  <el-dialog
    v-model="visible"
    class="command-dialog"
    width="min(680px, 92vw)"
    top="9vh"
    :show-close="false"
    append-to-body
    @opened="focusInput"
    @closed="reset"
  >
    <div class="cp">
      <div class="cp-search">
        <el-icon class="cp-search-icon"><Search /></el-icon>
        <input
          ref="inputRef"
          v-model="query"
          class="cp-input"
          type="text"
          placeholder="搜索动作、页面或快捷操作…"
          autocomplete="off"
          spellcheck="false"
          @keydown="onKeydown"
        />
        <kbd>ESC</kbd>
      </div>

      <div class="cp-body">
        <template v-for="(item, index) in items" :key="item.id">
          <div v-if="index === 0 || items[index - 1].group !== item.group" class="cp-group">
            {{ item.group }}
          </div>
          <button
            class="cp-item"
            :class="{ active: index === activeIndex }"
            type="button"
            @mouseenter="activeIndex = index"
            @click="choose(item)"
          >
            <span class="cp-icon"><el-icon><component :is="item.icon" /></el-icon></span>
            <span class="cp-text">
              <strong>{{ item.label }}</strong>
              <small v-if="item.hint">{{ item.hint }}</small>
            </span>
            <span v-if="item.badge" class="cp-badge">{{ item.badge }}</span>
          </button>
        </template>

        <div v-if="searching" class="cp-state">正在搜索动作库…</div>
        <div v-else-if="items.length === 0" class="cp-state">
          没有找到匹配结果，换个关键词试试
        </div>
      </div>

      <div class="cp-foot">
        <span><kbd>↑</kbd><kbd>↓</kbd> 选择</span>
        <span><kbd>Enter</kbd> 打开</span>
        <span><kbd>Esc</kbd> 关闭</span>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch, type Component } from 'vue'
import { useRouter } from 'vue-router'
import {
  Aim,
  DataAnalysis,
  HomeFilled,
  MagicStick,
  Moon,
  Reading,
  Search,
  Setting,
  Sunny,
  TrendCharts,
  User,
  VideoCamera,
} from '@element-plus/icons-vue'
import apiClient from '../api'
import { useTheme } from '../composables/useTheme'

interface PaletteItem {
  id: string
  label: string
  hint?: string
  badge?: string
  group: string
  icon: Component
  keywords?: string
  action: () => void
}

const router = useRouter()
const { resolved, toggle: toggleTheme } = useTheme()

const visible = ref(false)
const query = ref('')
const activeIndex = ref(0)
const inputRef = ref<HTMLInputElement | null>(null)
const exercises = ref<any[]>([])
const searching = ref(false)
let searchTimer: number | null = null
let requestId = 0

const go = (path: string) => {
  visible.value = false
  router.push(path)
}

const commands = computed<PaletteItem[]>(() => [
  {
    id: 'home',
    label: '回到首页',
    hint: '查看今日状态与训练洞察',
    group: '页面与操作',
    icon: HomeFilled,
    keywords: 'home dashboard 首页',
    action: () => go('/'),
  },
  {
    id: 'training',
    label: '开始智能训练',
    hint: '姿态识别 + 实时计数',
    group: '页面与操作',
    icon: VideoCamera,
    keywords: 'training workout 训练',
    action: () => go('/training'),
  },
  {
    id: 'ai-plan',
    label: '生成 AI 训练计划',
    group: '页面与操作',
    icon: MagicStick,
    keywords: 'plan ai 计划',
    action: () => go('/ai-plan'),
  },
  {
    id: 'posture',
    label: '姿态诊断',
    hint: '视觉大模型动作纠错',
    group: '页面与操作',
    icon: Aim,
    keywords: 'posture diagnosis 诊断',
    action: () => go('/posture-diagnosis'),
  },
  {
    id: 'exercises',
    label: '动作百科',
    group: '页面与操作',
    icon: Reading,
    keywords: 'exercise library 动作',
    action: () => go('/exercises'),
  },
  {
    id: 'graph',
    label: '动作知识图谱',
    group: '页面与操作',
    icon: TrendCharts,
    keywords: 'graph knowledge 图谱',
    action: () => go('/exercises/graph'),
  },
  {
    id: 'analytics',
    label: '训练数据中心',
    group: '页面与操作',
    icon: DataAnalysis,
    keywords: 'analytics data 数据',
    action: () => go('/analytics'),
  },
  {
    id: 'profile',
    label: '个人中心',
    group: '页面与操作',
    icon: User,
    keywords: 'profile account 个人',
    action: () => go('/profile'),
  },
  {
    id: 'theme',
    label: '切换明暗主题',
    badge: resolved.value === 'dark' ? '当前深色' : '当前浅色',
    group: '页面与操作',
    icon: resolved.value === 'dark' ? Sunny : Moon,
    keywords: 'theme dark light 主题 深色 浅色',
    action: () => {
      toggleTheme()
      visible.value = false
    },
  },
  {
    id: 'settings',
    label: '编辑个人资料',
    group: '页面与操作',
    icon: Setting,
    keywords: 'settings profile 设置',
    action: () => go('/profile'),
  },
])

const matchedCommands = computed(() => {
  const term = query.value.trim().toLowerCase()
  if (!term) return commands.value
  return commands.value.filter((command) =>
    `${command.label} ${command.hint || ''} ${command.keywords || ''}`.toLowerCase().includes(term),
  )
})

const exerciseItems = computed<PaletteItem[]>(() =>
  exercises.value.map((exercise) => ({
    id: `exercise-${exercise.id}`,
    label: exercise.name,
    hint: [exercise.target_muscle_display || exercise.target_muscle, exercise.difficulty_display]
      .filter(Boolean)
      .join(' · '),
    badge: '动作',
    group: '动作',
    icon: Aim,
    action: () => {
      visible.value = false
      router.push({
        path: '/training',
        query: { exercise_id: String(exercise.id), exercise_name: exercise.name },
      })
    },
  })),
)

const items = computed<PaletteItem[]>(() => [...matchedCommands.value, ...exerciseItems.value])

watch(query, () => {
  activeIndex.value = 0
  scheduleSearch()
})

watch(items, () => {
  if (activeIndex.value >= items.value.length) {
    activeIndex.value = Math.max(0, items.value.length - 1)
  }
})

function scheduleSearch() {
  if (searchTimer) window.clearTimeout(searchTimer)
  const term = query.value.trim()
  if (term.length < 1) {
    exercises.value = []
    searching.value = false
    return
  }

  const currentRequest = ++requestId
  searching.value = true
  searchTimer = window.setTimeout(async () => {
    try {
      const { data } = await apiClient.get('/exercises/', {
        params: { search: term, page_size: 6 },
      })
      if (currentRequest !== requestId) return
      exercises.value = data.results ?? data ?? []
    } catch {
      if (currentRequest === requestId) exercises.value = []
    } finally {
      if (currentRequest === requestId) searching.value = false
    }
  }, 260)
}

function focusInput() {
  nextTick(() => inputRef.value?.focus())
}

function reset() {
  query.value = ''
  activeIndex.value = 0
  exercises.value = []
  searching.value = false
  if (searchTimer) window.clearTimeout(searchTimer)
}

function choose(item: PaletteItem) {
  item.action()
}

function move(delta: number) {
  if (!items.value.length) return
  activeIndex.value = (activeIndex.value + delta + items.value.length) % items.value.length
  nextTick(() => {
    document.querySelector('.cp-item.active')?.scrollIntoView({ block: 'nearest' })
  })
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    move(1)
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    move(-1)
  } else if (event.key === 'Enter') {
    event.preventDefault()
    const item = items.value[activeIndex.value]
    if (item) choose(item)
  } else if (event.key === 'Escape') {
    visible.value = false
  }
}

function onGlobalKeydown(event: KeyboardEvent) {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    if (visible.value) {
      visible.value = false
    } else {
      open()
    }
  }
}

function open() {
  visible.value = true
}

onMounted(() => window.addEventListener('keydown', onGlobalKeydown))
onUnmounted(() => {
  window.removeEventListener('keydown', onGlobalKeydown)
  if (searchTimer) window.clearTimeout(searchTimer)
})

defineExpose({ open })
</script>

<style scoped>
.cp {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: 18px;
}

.cp-search {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 18px 20px;
  border-bottom: 1px solid var(--fv-border);
}

.cp-search-icon {
  color: var(--fv-text-2);
  font-size: 20px;
}

.cp-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  color: var(--fv-text);
  font-size: 16px;
  font-family: inherit;
}

.cp-input::placeholder {
  color: var(--fv-text-2);
}

.cp-search kbd,
.cp-foot kbd {
  border: 1px solid var(--fv-border);
  background: var(--fv-surface-2);
  color: var(--fv-text-2);
  border-radius: 6px;
  padding: 2px 6px;
  font-size: 11px;
  font-family: inherit;
}

.cp-body {
  max-height: min(58vh, 480px);
  overflow-y: auto;
  padding: 8px;
}

.cp-group {
  padding: 12px 12px 6px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--fv-text-2);
}

.cp-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border: none;
  border-radius: 12px;
  background: transparent;
  color: var(--fv-text);
  text-align: left;
  cursor: pointer;
  transition: background 0.15s ease;
}

.cp-item.active {
  background: var(--fv-primary-soft);
}

.cp-icon {
  flex: none;
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  background: var(--fv-surface-2);
  color: var(--fv-primary);
}

.cp-text {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.cp-text strong {
  font-size: 14px;
  font-weight: 650;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cp-text small {
  font-size: 12px;
  color: var(--fv-text-2);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cp-badge {
  flex: none;
  font-size: 11px;
  color: var(--fv-text-2);
  padding: 3px 8px;
  border-radius: 999px;
  border: 1px solid var(--fv-border);
}

.cp-state {
  padding: 28px 16px;
  text-align: center;
  font-size: 13px;
  color: var(--fv-text-2);
}

.cp-foot {
  display: flex;
  gap: 18px;
  padding: 12px 20px;
  border-top: 1px solid var(--fv-border);
  font-size: 11.5px;
  color: var(--fv-text-2);
}

.cp-foot span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

:global(.command-dialog) {
  padding: 0 !important;
  background: var(--fv-surface) !important;
  border: 1px solid var(--fv-border);
  border-radius: 20px !important;
  box-shadow: var(--fv-shadow-lg) !important;
}

:global(.command-dialog .el-dialog__header) {
  display: none;
}

:global(.command-dialog .el-dialog__body) {
  padding: 0;
}
</style>

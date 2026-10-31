<script setup lang="ts">
import { computed, ref } from 'vue'
import { ArrowLeft, ArrowRight } from '@element-plus/icons-vue'
import { buildMonthGrid, countActiveInGrid } from '../utils/calendar'

const props = defineProps<{
  /** ISO day keys (YYYY-MM-DD) that contain at least one session. */
  activeDays: readonly string[]
}>()

const today = new Date()
const year = ref(today.getFullYear())
const month = ref(today.getMonth() + 1)

const WEEK_LABELS = ['一', '二', '三', '四', '五', '六', '日']

const weeks = computed(() => buildMonthGrid(year.value, month.value, props.activeDays))
const activeCount = computed(() => countActiveInGrid(weeks.value))
const title = computed(() => `${year.value} 年 ${month.value} 月`)
const isCurrentMonth = computed(
  () => year.value === today.getFullYear() && month.value === today.getMonth() + 1,
)

const shift = (delta: number) => {
  let nextMonth = month.value + delta
  let nextYear = year.value
  if (nextMonth < 1) {
    nextMonth = 12
    nextYear -= 1
  } else if (nextMonth > 12) {
    nextMonth = 1
    nextYear += 1
  }
  month.value = nextMonth
  year.value = nextYear
}
</script>

<template>
  <section class="calendar">
    <header class="calendar-head">
      <div>
        <p class="calendar-title">{{ title }}</p>
        <p class="calendar-sub">本月训练 {{ activeCount }} 天</p>
      </div>

      <div class="calendar-nav">
        <button type="button" aria-label="上一个月" @click="shift(-1)">
          <el-icon><ArrowLeft /></el-icon>
        </button>
        <button
          type="button"
          class="today-btn"
          :disabled="isCurrentMonth"
          @click="
            () => {
              year = today.getFullYear()
              month = today.getMonth() + 1
            }
          "
        >
          回到本月
        </button>
        <button type="button" aria-label="下一个月" @click="shift(1)">
          <el-icon><ArrowRight /></el-icon>
        </button>
      </div>
    </header>

    <div class="calendar-grid" role="grid" :aria-label="`${title}训练日历`">
      <span v-for="label in WEEK_LABELS" :key="label" class="weekday">{{ label }}</span>

      <template v-for="(week, wi) in weeks" :key="wi">
        <span
          v-for="(cell, ci) in week"
          :key="`${wi}-${ci}`"
          class="cell"
          :class="{
            outside: !cell.inMonth,
            active: cell.active,
            today: cell.key === `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`,
          }"
          :title="cell.active ? `${cell.key} 有训练记录` : cell.key"
        >
          {{ cell.day }}
        </span>
      </template>
    </div>
  </section>
</template>

<style scoped>
.calendar {
  padding: 16px;
  border: 1px solid var(--fv-border);
  border-radius: var(--fv-radius-md);
  background: var(--fv-surface);
}

.calendar-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.calendar-title {
  margin: 0;
  font-size: 15px;
  font-weight: 800;
  letter-spacing: -0.01em;
  color: var(--fv-text);
}

.calendar-sub {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--fv-text-2);
}

.calendar-nav {
  display: flex;
  align-items: center;
  gap: 6px;
}

.calendar-nav button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 28px;
  height: 28px;
  padding: 0 8px;
  border: 1px solid var(--fv-border);
  border-radius: var(--fv-radius-sm);
  background: var(--fv-surface);
  color: var(--fv-text-2);
  font-size: 12px;
  cursor: pointer;
  transition: border-color 0.15s ease, color 0.15s ease;
}

.calendar-nav button:hover:not(:disabled) {
  border-color: var(--fv-border-strong);
  color: var(--fv-text);
}

.calendar-nav button:disabled {
  opacity: 0.45;
  cursor: default;
}

.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 4px;
}

.weekday {
  font-size: 11px;
  text-align: center;
  color: var(--fv-text-3);
}

.cell {
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--fv-radius-sm);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  color: var(--fv-text-2);
  background: var(--fv-surface-2);
}

.cell.outside {
  opacity: 0.35;
}

.cell.active {
  background: var(--fv-primary);
  color: #fff;
  font-weight: 700;
}

.cell.today {
  outline: 2px solid var(--fv-accent);
  outline-offset: -2px;
}
</style>

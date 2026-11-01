<script setup lang="ts">
/**
 * 训练周期化计划（中周期）。
 *
 * 数据来自后端 `utils/periodization.py`：把分肌群恢复、整体准备度与 e1RM 处方
 * 合成为一份 3–6 周的周计划。这里负责把它排成可读的周视图。
 */
import { computed, ref } from 'vue'

import {
  autoregulationText,
  exerciseText,
  intensityHint,
  phaseLabel,
  phaseTone,
  slotText,
  volumeHint,
  type MesocyclePayload,
  type MesocycleWeek,
} from '../utils/periodization'

const props = defineProps<{
  plan: MesocyclePayload | null
}>()

const activeWeek = ref(1)

const weeks = computed<MesocycleWeek[]>(() => props.plan?.weeks ?? [])

const current = computed<MesocycleWeek | null>(
  () => weeks.value.find((item) => item.index === activeWeek.value) ?? weeks.value[0] ?? null,
)

const summary = computed(() => {
  const plan = props.plan
  if (!plan) return null
  return {
    readiness: Math.round(plan.readiness),
    days: plan.days_per_week,
    totalSets: plan.total_sets,
    autoregulation: autoregulationText(plan.autoregulation),
  }
})

const weekBars = computed(() =>
  weeks.value.map((week) => {
    const max = Math.max(...weeks.value.map((item) => item.total_sets), 1)
    return {
      index: week.index,
      label: phaseLabel(week.phase),
      tone: phaseTone(week.phase),
      sets: week.total_sets,
      height: `${Math.max(8, Math.round((week.total_sets / max) * 100))}%`,
    }
  }),
)

function selectWeek(index: number) {
  activeWeek.value = index
}
</script>

<template>
  <div v-if="plan && weeks.length > 0" class="mesocycle">
    <div class="cycle-summary">
      <div class="summary-item">
        <span>准备度</span>
        <strong>{{ summary?.readiness ?? 0 }}</strong>
      </div>
      <div class="summary-item">
        <span>每周训练</span>
        <strong>{{ summary?.days ?? 0 }}<small> 天</small></strong>
      </div>
      <div class="summary-item">
        <span>周期总组数</span>
        <strong>{{ summary?.totalSets ?? 0 }}</strong>
      </div>
      <div class="summary-item">
        <span>容量调节</span>
        <strong class="summary-text">{{ summary?.autoregulation ?? '容量正常' }}</strong>
      </div>
    </div>

    <ul class="cycle-bars">
      <li v-for="bar in weekBars" :key="bar.index">
        <button
          type="button"
          class="cycle-bar"
          :class="[`tone-${bar.tone}`, { active: current?.index === bar.index }]"
          :aria-label="`第 ${bar.index} 周 ${bar.label}，${bar.sets} 组`"
          @click="selectWeek(bar.index)"
        >
          <span class="cycle-bar-track">
            <span class="cycle-bar-fill" :style="{ height: bar.height }"></span>
          </span>
          <span class="cycle-bar-label">{{ bar.label }}</span>
          <span class="cycle-bar-week">W{{ bar.index }}</span>
        </button>
      </li>
    </ul>

    <section v-if="current" class="cycle-week">
      <header class="cycle-week-head">
        <div>
          <h4>
            第 {{ current.index }} 周 · {{ phaseLabel(current.phase) }}
          </h4>
          <p>{{ current.note }}</p>
        </div>
        <div class="cycle-week-meta">
          <span>{{ volumeHint(current.volume) }}</span>
          <span>{{ intensityHint(current.intensity) }}</span>
          <span>{{ current.reps_low }}–{{ current.reps_high }} 次</span>
        </div>
      </header>

      <div class="cycle-days">
        <article v-for="session in current.sessions" :key="session.index" class="cycle-day">
          <div class="cycle-day-head">
            <strong>{{ session.label }}</strong>
            <span>{{ session.total_sets }} 组</span>
          </div>
          <ul class="cycle-slots">
            <li v-for="slot in session.slots" :key="slot.muscle" class="cycle-slot">
              <span class="slot-muscle">{{ slot.label }}</span>
              <span class="slot-detail">{{ slotText(slot) }}</span>
              <span v-if="slot.based_on_e1rm" class="slot-tag">e1RM 折算</span>
              <ul v-if="slot.exercises.length > 0" class="slot-exercises">
                <li v-for="exercise in slot.exercises" :key="exercise.exercise_id">
                  {{ exerciseText(exercise) }}
                </li>
              </ul>
            </li>
          </ul>
        </article>
      </div>
    </section>

    <ul v-if="plan.notes.length > 0" class="cycle-notes">
      <li v-for="note in plan.notes" :key="note">{{ note }}</li>
    </ul>
  </div>
</template>

<style scoped>
.mesocycle {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.cycle-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
  gap: 10px;
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 9px 11px;
  border-radius: var(--fv-radius-sm);
  background: var(--fv-surface-2);
}

.summary-item span {
  font-size: 11px;
  color: var(--fv-text-3);
}

.summary-item strong {
  font-size: 17px;
  font-weight: 650;
  color: var(--fv-text-1);
  font-variant-numeric: tabular-nums;
}

.summary-item strong small {
  font-size: 11px;
  font-weight: 500;
  color: var(--fv-text-3);
}

.summary-text {
  font-size: 13px !important;
}

.cycle-bars {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  align-items: flex-end;
  gap: 8px;
}

.cycle-bar {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  padding: 0;
  border: none;
  background: transparent;
  cursor: pointer;
  font: inherit;
}

.cycle-bar-track {
  width: 100%;
  height: 56px;
  display: flex;
  align-items: flex-end;
  border-radius: var(--fv-radius-sm);
  background: var(--fv-surface-2);
  overflow: hidden;
}

.cycle-bar-fill {
  width: 100%;
  border-radius: var(--fv-radius-sm);
  background: var(--fv-primary-soft);
  border-top: 2px solid var(--fv-primary);
  transition: height 0.3s ease;
}

.cycle-bar.active .cycle-bar-fill {
  background: var(--fv-primary);
}

.cycle-bar.tone-intense .cycle-bar-fill {
  border-top-color: var(--fv-warning);
}

.cycle-bar.tone-peak .cycle-bar-fill {
  border-top-color: var(--fv-danger);
}

.cycle-bar.tone-rest .cycle-bar-fill {
  border-top-color: var(--fv-text-3);
  background: var(--fv-surface-3);
}

.cycle-bar-label {
  font-size: 11.5px;
  color: var(--fv-text-2);
}

.cycle-bar.active .cycle-bar-label {
  color: var(--fv-primary);
  font-weight: 600;
}

.cycle-bar-week {
  font-size: 10.5px;
  color: var(--fv-text-3);
  font-variant-numeric: tabular-nums;
}

.cycle-week {
  border-top: 1px solid var(--fv-surface-2);
  padding-top: 12px;
}

.cycle-week-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.cycle-week-head h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 650;
  color: var(--fv-text-1);
}

.cycle-week-head p {
  margin: 3px 0 0;
  font-size: 12px;
  color: var(--fv-text-3);
  line-height: 1.5;
}

.cycle-week-meta {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px;
}

.cycle-week-meta span {
  font-size: 11px;
  padding: 2px 7px;
  border-radius: 999px;
  background: var(--fv-surface-2);
  color: var(--fv-text-2);
  white-space: nowrap;
}

.cycle-days {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 10px;
}

.cycle-day {
  border: 1px solid var(--fv-border);
  border-radius: var(--fv-radius-md);
  padding: 10px 11px;
  background: var(--fv-surface);
}

.cycle-day-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 7px;
}

.cycle-day-head strong {
  font-size: 12.5px;
  color: var(--fv-text-1);
}

.cycle-day-head span {
  font-size: 11px;
  color: var(--fv-text-3);
  font-variant-numeric: tabular-nums;
}

.cycle-slots {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.cycle-slot {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 6px;
}

.slot-muscle {
  font-size: 12px;
  font-weight: 600;
  color: var(--fv-text-1);
  min-width: 34px;
}

.slot-detail {
  font-size: 11.5px;
  color: var(--fv-text-2);
  font-variant-numeric: tabular-nums;
}

.slot-tag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 999px;
  background: var(--fv-accent-soft);
  color: var(--fv-accent);
}

.slot-exercises {
  list-style: none;
  margin: 2px 0 0;
  padding: 0 0 0 40px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  width: 100%;
}

.slot-exercises li {
  font-size: 11px;
  color: var(--fv-text-3);
  line-height: 1.45;
}

.cycle-notes {
  list-style: none;
  margin: 0;
  padding: 9px 11px;
  border-radius: var(--fv-radius-sm);
  background: var(--fv-surface-2);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.cycle-notes li {
  font-size: 11.5px;
  color: var(--fv-text-2);
  line-height: 1.5;
}
</style>

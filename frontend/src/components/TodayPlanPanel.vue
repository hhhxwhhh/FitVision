<script setup lang="ts">
/**
 * 今日处方：中周期计划落到今天该做的动作。
 *
 * 数据来自后端 `utils/periodization.py` 的 `/api/growth/mesocycle/`：
 * 当前阶段、今天这一训练日的动作与重量都在里面。这里负责把它排成可执行的清单。
 */
import { computed } from 'vue'

import {
  autoregulationText,
  exerciseText,
  phaseLabel,
  phaseTone,
  todaySession,
  type MesocyclePayload,
  type MesocycleSession,
  type MesocycleWeek,
} from '../utils/periodization'

const props = defineProps<{
  plan: MesocyclePayload | null
  weekday?: number
}>()

const week = computed<MesocycleWeek | null>(() => props.plan?.weeks[0] ?? null)

const session = computed<MesocycleSession | null>(() => todaySession(props.plan, props.weekday ?? 1))

const tone = computed(() => phaseTone(week.value?.phase))

const summary = computed(() => {
  const plan = props.plan
  if (!plan || !week.value) return null
  return {
    phase: phaseLabel(week.value.phase),
    note: week.value.note,
    reps: `${week.value.reps_low}–${week.value.reps_high} 次`,
    autoregulation: autoregulationText(plan.autoregulation),
  }
})

/** 今天这一训练日里所有肌群安排下的具体动作。 */
const exercises = computed(() => (session.value?.slots ?? []).flatMap((slot) => slot.exercises))
</script>

<template>
  <div v-if="plan && week && session" class="today-plan" :class="`tone-${tone}`">
    <div class="today-head">
      <div class="today-phase">
        <span class="phase-tag">{{ summary?.phase }}</span>
        <strong>{{ session.label }}</strong>
      </div>
      <div class="today-meta">
        <span>{{ summary?.reps }}</span>
        <span>{{ summary?.autoregulation }}</span>
      </div>
    </div>

    <p class="today-note">{{ summary?.note }}</p>

    <ul v-if="exercises.length > 0" class="today-exercises">
      <li v-for="exercise in exercises" :key="exercise.exercise_id" class="today-exercise">
        <span class="exercise-name">{{ exercise.name }}</span>
        <span class="exercise-detail">{{ exerciseText(exercise) }}</span>
        <span v-if="exercise.based_on_e1rm" class="exercise-tag">e1RM 折算</span>
      </li>
    </ul>

    <p v-else class="today-empty">
      今天这个训练日是恢复日 —— 趁身体还在适应期，安排一点拉伸或散步就够了。
    </p>
  </div>
</template>

<style scoped>
.today-plan {
  display: flex;
  flex-direction: column;
  gap: 9px;
  padding: 12px 13px;
  border-radius: var(--fv-radius-md);
  background: var(--fv-surface-2);
  border-left: 3px solid var(--fv-primary);
}

.today-plan.tone-intense {
  border-left-color: var(--fv-warning);
}

.today-plan.tone-peak {
  border-left-color: var(--fv-danger);
}

.today-plan.tone-rest {
  border-left-color: var(--fv-text-3);
}

.today-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.today-phase {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.phase-tag {
  font-size: 10.5px;
  padding: 1px 7px;
  border-radius: 999px;
  background: var(--fv-primary-soft);
  color: var(--fv-primary);
}

.tone-intense .phase-tag {
  background: rgba(180, 83, 9, 0.12);
  color: var(--fv-warning);
}

.tone-peak .phase-tag {
  background: rgba(185, 28, 28, 0.1);
  color: var(--fv-danger);
}

.tone-rest .phase-tag {
  background: var(--fv-surface-3);
  color: var(--fv-text-2);
}

.today-phase strong {
  font-size: 13.5px;
  font-weight: 650;
  color: var(--fv-text-1);
}

.today-meta {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.today-meta span {
  font-size: 11px;
  color: var(--fv-text-3);
  white-space: nowrap;
}

.today-note {
  margin: 0;
  font-size: 11.5px;
  line-height: 1.55;
  color: var(--fv-text-2);
}

.today-exercises {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.today-exercise {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 7px;
}

.exercise-name {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--fv-text-1);
}

.exercise-detail {
  font-size: 11.5px;
  color: var(--fv-text-2);
  font-variant-numeric: tabular-nums;
}

.exercise-tag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 999px;
  background: var(--fv-accent-soft);
  color: var(--fv-accent);
}

.today-empty {
  margin: 0;
  font-size: 11.5px;
  line-height: 1.55;
  color: var(--fv-text-3);
}
</style>

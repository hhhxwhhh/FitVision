<script setup lang="ts">
/**
 * 今日分肌群恢复状态。
 *
 * 数据来自后端 `utils/recovery.py`：每个肌群的残余疲劳按指数半衰期衰减，
 * 这里只负责把它画成一条条可读的进度条，并给出"优先练 / 先避开"的结论。
 */
import { computed } from 'vue'

import {
  hoursToReadyText,
  labelsFor,
  multiplierHint,
  recoveryStatus,
  sortByFatigue,
  statusLabel,
  volumeHint,
  type MuscleRecoveryState,
} from '../utils/muscleRecovery'

const props = defineProps<{
  states: MuscleRecoveryState[]
  focus?: string[]
  avoid?: string[]
}>()

const rows = computed(() => sortByFatigue(props.states ?? []))

const focusLabels = computed(() => labelsFor(rows.value, props.focus ?? []))
const avoidLabels = computed(() => labelsFor(rows.value, props.avoid ?? []))

const hasAdvice = computed(() => focusLabels.value.length > 0 || avoidLabels.value.length > 0)

const toneOf = (item: MuscleRecoveryState) => recoveryStatus(item.recovery)
</script>

<template>
  <div v-if="rows.length > 0" class="muscle-recovery">
    <ul class="muscle-list">
      <li v-for="item in rows" :key="item.muscle" class="muscle-row" :class="`tone-${toneOf(item)}`">
        <div class="muscle-head">
          <span class="muscle-name">{{ item.label }}</span>
          <span class="muscle-meta">
            <span class="muscle-status">{{ statusLabel(toneOf(item)) }}</span>
            <span class="muscle-value">{{ Math.round(item.recovery) }}%</span>
          </span>
        </div>

        <div class="muscle-bar">
          <div class="muscle-bar-fill" :style="{ width: `${item.recovery}%` }" />
        </div>

        <p class="muscle-hint">
          {{ multiplierHint(item.multiplier) }} · {{ volumeHint(item.volume_status) }}（本周
          {{ Math.round(item.weekly_sets) }} 组）· {{ hoursToReadyText(item.hours_to_ready) }}
        </p>
      </li>
    </ul>

    <div v-if="hasAdvice" class="muscle-advice">
      <p v-if="focusLabels.length > 0" class="advice-line advice-go">
        今天优先：<strong>{{ focusLabels.join(' / ') }}</strong>
      </p>
      <p v-if="avoidLabels.length > 0" class="advice-line advice-wait">
        先让它们恢复：<strong>{{ avoidLabels.join(' / ') }}</strong>
      </p>
    </div>
  </div>
</template>

<style scoped>
.muscle-recovery {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.muscle-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.muscle-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 5px;
}

.muscle-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--fv-text-1);
}

.muscle-meta {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.muscle-status {
  font-size: 11px;
  color: var(--fv-text-3);
}

.muscle-value {
  font-size: 12px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  color: var(--fv-text-2);
}

.muscle-bar {
  height: 6px;
  border-radius: 999px;
  background: var(--fv-surface-2);
  overflow: hidden;
}

.muscle-bar-fill {
  height: 100%;
  border-radius: 999px;
  background: var(--fv-primary);
  transition: width 0.35s ease;
}

.muscle-hint {
  margin: 5px 0 0;
  font-size: 11.5px;
  line-height: 1.5;
  color: var(--fv-text-3);
}

.tone-caution .muscle-bar-fill {
  background: var(--fv-warning);
}

.tone-fatigued .muscle-bar-fill {
  background: var(--fv-danger);
}

.tone-fatigued .muscle-value {
  color: var(--fv-warning);
}

.muscle-advice {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-top: 4px;
  border-top: 1px solid var(--fv-surface-2);
}

.advice-line {
  margin: 0;
  font-size: 12px;
  color: var(--fv-text-2);
}

.advice-line strong {
  color: var(--fv-text-1);
}

.advice-go strong {
  color: var(--fv-primary);
}

.advice-wait strong {
  color: var(--fv-warning);
}
</style>

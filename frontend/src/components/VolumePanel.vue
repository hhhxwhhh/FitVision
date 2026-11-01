<script setup lang="ts">
/**
 * 训练容量（Volume）。
 *
 * 数据来自后端 `utils/volume.py`：把训练量换成"抗极端组主导"的有效容量，
 * 再从肌群结构与周趋势两个角度回答"我的容量够不够、均不均衡"。
 */
import { computed } from 'vue'

import {
  concentrationLabel,
  formatVolume,
  muscleStatusLabel,
  trendLabel,
  trendTone,
  type VolumeMuscle,
  type VolumePayload,
} from '../utils/volume'

const props = defineProps<{
  report: VolumePayload | null
}>()

const muscles = computed<VolumeMuscle[]>(() => props.report?.muscles ?? [])

/** 容量占比条的最大值，用来把占比换算成百分比宽度。 */
const maxShare = computed(() =>
  muscles.value.reduce((max, item) => Math.max(max, item.share), 0),
)

/** 每一行相对最大占比的宽度，避免占比很小时条子看不见。 */
function barWidth(muscle: VolumeMuscle): string {
  if (maxShare.value <= 0) return '0%'
  return `${Math.max(4, Math.round((muscle.share / maxShare.value) * 100))}%`
}

/** 周趋势的柱状图：按历史最大值归一化。 */
const weekBars = computed(() => {
  const weeks = props.report?.weekly ?? []
  const max = weeks.reduce((value, item) => Math.max(value, item.effective_volume), 0)
  return weeks.map((item) => ({
    ...item,
    height: max > 0 ? Math.max(6, Math.round((item.effective_volume / max) * 100)) : 6,
  }))
})

const trend = computed(() => props.report?.trend ?? 'unknown')
</script>

<template>
  <div v-if="report && report.available && muscles.length > 0" class="volume">
    <div class="volume-summary">
      <div class="summary-item">
        <span>有效容量</span>
        <strong>{{ formatVolume(report.total_effective_volume) }}<small> kg·次</small></strong>
      </div>
      <div class="summary-item">
        <span>结构</span>
        <strong class="summary-text">{{ concentrationLabel(report.concentration) }}</strong>
      </div>
      <div class="summary-item">
        <span>趋势</span>
        <strong class="summary-text" :class="`tone-${trendTone(trend)}`">
          {{ trendLabel(trend) }}
        </strong>
      </div>
      <div class="summary-item">
        <span>结论</span>
        <strong class="summary-text">{{ report.verdict }}</strong>
      </div>
    </div>

    <ul class="volume-muscles">
      <li v-for="muscle in muscles" :key="muscle.muscle" class="volume-muscle">
        <div class="muscle-head">
          <span class="muscle-name">{{ muscle.label }}</span>
          <span class="muscle-share">{{ Math.round(muscle.share * 100) }}%</span>
        </div>
        <div class="muscle-track">
          <span class="muscle-fill" :style="{ width: barWidth(muscle) }"></span>
        </div>
        <span class="muscle-detail">
          {{ muscle.sets }} 组/周 · 有效 {{ formatVolume(muscle.effective_volume) }}
          <em class="muscle-status" :class="`status-${muscle.status}`">
            {{ muscleStatusLabel(muscle.status) }}
          </em>
        </span>
      </li>
    </ul>

    <div v-if="weekBars.length > 0" class="volume-weeks">
      <span class="weeks-title">每周有效容量</span>
      <div class="weeks-chart">
        <span
          v-for="week in weekBars"
          :key="`${week.year}-${week.week}`"
          class="week-bar"
          :style="{ height: `${week.height}%` }"
          :title="`第 ${week.week} 周 · ${formatVolume(week.effective_volume)} kg·次`"
        ></span>
      </div>
      <span class="weeks-hint">柱子越高，那周的容量越大。</span>
    </div>

    <ul v-if="report.advice.length > 0" class="volume-advice">
      <li v-for="advice in report.advice" :key="advice">{{ advice }}</li>
    </ul>

    <details v-if="report.sessions.length > 0" class="volume-detail">
      <summary>逐次训练明细</summary>
      <ul class="detail-list">
        <li v-for="session in report.sessions" :key="session.date">
          <span class="detail-date">{{ session.date || '—' }}</span>
          <span class="detail-sets">{{ session.sets }} 组</span>
          <span class="detail-load">{{ formatVolume(session.effective_volume) }} kg·次</span>
        </li>
      </ul>
    </details>
  </div>

  <div v-else-if="report" class="volume-empty">
    <p>{{ report.reason || '还没有带重量的训练记录，补上重量后就能看到容量结构。' }}</p>
  </div>
</template>

<style scoped>
.volume {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.volume-summary {
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

.tone-up {
  color: var(--fv-success);
}

.tone-down {
  color: var(--fv-danger);
}

.tone-flat {
  color: var(--fv-text-1);
}

.volume-muscles {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.volume-muscle {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.muscle-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}

.muscle-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--fv-text-1);
}

.muscle-share {
  font-size: 13px;
  color: var(--fv-text-2);
  font-variant-numeric: tabular-nums;
}

.muscle-track {
  position: relative;
  height: 8px;
  border-radius: var(--fv-radius-sm);
  background: var(--fv-surface-2);
  overflow: hidden;
}

.muscle-fill {
  display: block;
  height: 100%;
  border-radius: var(--fv-radius-sm);
  background: var(--fv-primary-soft);
  border-right: 2px solid var(--fv-primary);
}

.muscle-detail {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11.5px;
  color: var(--fv-text-3);
}

.muscle-status {
  font-style: normal;
  padding: 0 6px;
  border-radius: 999px;
  font-size: 11px;
}

.muscle-status.status-ok {
  background: color-mix(in srgb, var(--fv-success) 16%, var(--fv-surface-2));
  color: var(--fv-success);
}

.muscle-status.status-low {
  background: color-mix(in srgb, var(--fv-warning) 18%, var(--fv-surface-2));
  color: var(--fv-warning);
}

.muscle-status.status-high {
  background: color-mix(in srgb, var(--fv-danger) 16%, var(--fv-surface-2));
  color: var(--fv-danger);
}

.muscle-status.status-unknown {
  background: var(--fv-surface-3);
  color: var(--fv-text-3);
}

.volume-weeks {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.weeks-title {
  font-size: 12.5px;
  color: var(--fv-text-2);
}

.weeks-chart {
  display: flex;
  align-items: flex-end;
  gap: 6px;
  height: 56px;
  padding: 6px 0;
  border-bottom: 1px solid var(--fv-surface-3);
}

.week-bar {
  flex: 1;
  min-width: 8px;
  border-radius: var(--fv-radius-sm) var(--fv-radius-sm) 0 0;
  background: var(--fv-primary-soft);
  border-bottom: 2px solid var(--fv-primary);
}

.weeks-hint {
  font-size: 11.5px;
  color: var(--fv-text-3);
}

.volume-advice {
  list-style: none;
  margin: 0;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  border-radius: var(--fv-radius-sm);
  background: color-mix(in srgb, var(--fv-warning) 12%, var(--fv-surface-2));
  color: var(--fv-text-1);
  font-size: 12.5px;
  line-height: 1.6;
}

.volume-detail summary {
  font-size: 12.5px;
  color: var(--fv-text-2);
  cursor: pointer;
}

.detail-list {
  list-style: none;
  margin: 8px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.detail-list li {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12.5px;
  color: var(--fv-text-2);
}

.detail-date {
  font-variant-numeric: tabular-nums;
  min-width: 84px;
}

.detail-sets {
  min-width: 52px;
}

.detail-load {
  color: var(--fv-text-3);
  font-variant-numeric: tabular-nums;
}

.volume-empty {
  padding: 14px;
  border-radius: var(--fv-radius-sm);
  background: var(--fv-surface-2);
}

.volume-empty p {
  margin: 0;
  font-size: 13px;
  color: var(--fv-text-2);
}
</style>

<script setup lang="ts">
/**
 * 训练强度分布（TRIMP）。
 *
 * 数据来自后端 `utils/trimp.py`：把训练拆到四个强度区间上，
 * 回答"我的高强度组是不是练太多"。这里负责把它排成可读的分布视图。
 */
import { computed } from 'vue'

import {
  balanceLabel,
  zoneTone,
  type IntensityPayload,
  type IntensitySession,
  type IntensityZone,
} from '../utils/intensity'

const props = defineProps<{
  report: IntensityPayload | null
}>()

const sessions = computed<IntensitySession[]>(() => props.report?.sessions ?? [])

/** 汇总所有训练日的区间分布，得到总体占比。 */
const overall = computed<IntensityZone[]>(() => {
  const zones = new Map<string, IntensityZone>()
  let total = 0
  for (const session of sessions.value) {
    for (const zone of session.zones) {
      const current = zones.get(zone.key)
      if (current) {
        current.sets += zone.sets
        current.load += zone.load
      } else {
        zones.set(zone.key, { ...zone })
      }
      total += zone.sets
    }
  }
  if (total === 0) return []
  return Array.from(zones.values()).map((zone) => ({
    ...zone,
    share: zone.sets / total,
  }))
})

/** 目标占比的参考线，用于对照"应该长什么样"。 */
const targets = computed(() => {
  const map = new Map<string, number>()
  for (const zone of overall.value) {
    map.set(zone.key, zone.target_share)
  }
  return map
})

const highIntensitySets = computed(() =>
  sessions.value.reduce((sum, session) => sum + session.high_intensity_sets, 0),
)

const unbalancedSessions = computed(
  () => sessions.value.filter((session) => !session.balanced).length,
)
</script>

<template>
  <div v-if="report && report.available && overall.length > 0" class="intensity">
    <div class="intensity-summary">
      <div class="summary-item">
        <span>强度分布</span>
        <strong class="summary-text">{{ balanceLabel(report.balance_score) }}</strong>
      </div>
      <div class="summary-item">
        <span>高强度组</span>
        <strong>{{ highIntensitySets }}<small> 组</small></strong>
      </div>
      <div class="summary-item">
        <span>训练次数</span>
        <strong>{{ sessions.length }}<small> 次</small></strong>
      </div>
      <div class="summary-item">
        <span>失衡训练</span>
        <strong>{{ unbalancedSessions }}<small> 次</small></strong>
      </div>
    </div>

    <ul class="intensity-zones">
      <li v-for="zone in overall" :key="zone.key" class="intensity-zone">
        <div class="zone-head">
          <span class="zone-name">{{ zone.label }}</span>
          <span class="zone-share">{{ Math.round(zone.share * 100) }}%</span>
        </div>
        <div class="zone-track">
          <span
            class="zone-fill"
            :class="`tone-${zoneTone(zone.key)}`"
            :style="{ width: `${Math.round(zone.share * 100)}%` }"
          ></span>
          <span
            class="zone-target"
            :style="{ left: `${Math.round((targets.get(zone.key) ?? 0) * 100)}%` }"
            :title="`建议占比 ${Math.round((targets.get(zone.key) ?? 0) * 100)}%`"
          ></span>
        </div>
        <span class="zone-detail">{{ zone.sets }} 组 · 建议 {{ Math.round((targets.get(zone.key) ?? 0) * 100) }}%</span>
      </li>
    </ul>

    <p class="intensity-hint">竖线是建议占比，用来对照你现在练得偏重还是偏轻。</p>

    <ul v-if="report.advice.length > 0" class="intensity-advice">
      <li v-for="advice in report.advice" :key="advice">{{ advice }}</li>
    </ul>

    <details v-if="sessions.length > 0" class="intensity-detail">
      <summary>逐次训练明细</summary>
      <ul class="detail-list">
        <li v-for="session in sessions" :key="session.date">
          <span class="detail-date">{{ session.date || '—' }}</span>
          <span class="detail-sets">{{ session.sets }} 组</span>
          <span class="detail-tag" :class="{ warn: !session.balanced }">
            {{ session.balanced ? '分布均衡' : '强度偏高' }}
          </span>
        </li>
      </ul>
    </details>
  </div>

  <div v-else-if="report" class="intensity-empty">
    <p>{{ report.reason || '还没有带重量或 RPE 的训练记录，补上就能看到强度分布。' }}</p>
  </div>
</template>

<style scoped>
.intensity {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.intensity-summary {
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

.intensity-zones {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.intensity-zone {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.zone-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}

.zone-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--fv-text-1);
}

.zone-share {
  font-size: 13px;
  color: var(--fv-text-2);
  font-variant-numeric: tabular-nums;
}

.zone-track {
  position: relative;
  height: 10px;
  border-radius: var(--fv-radius-sm);
  background: var(--fv-surface-2);
  overflow: hidden;
}

.zone-fill {
  display: block;
  height: 100%;
  border-radius: var(--fv-radius-sm);
  background: var(--fv-primary-soft);
  border-right: 2px solid var(--fv-primary);
}

.zone-fill.tone-calm {
  background: var(--fv-surface-3);
  border-right-color: var(--fv-text-3);
}

.zone-fill.tone-steady {
  background: color-mix(in srgb, var(--fv-success) 22%, var(--fv-surface-2));
  border-right-color: var(--fv-success);
}

.zone-fill.tone-warm {
  background: color-mix(in srgb, var(--fv-warning) 24%, var(--fv-surface-2));
  border-right-color: var(--fv-warning);
}

.zone-fill.tone-hot {
  background: color-mix(in srgb, var(--fv-danger) 22%, var(--fv-surface-2));
  border-right-color: var(--fv-danger);
}

.zone-target {
  position: absolute;
  top: 0;
  width: 2px;
  height: 100%;
  background: var(--fv-text-2);
  opacity: 0.65;
}

.zone-detail {
  font-size: 11.5px;
  color: var(--fv-text-3);
}

.intensity-hint {
  margin: 0;
  font-size: 12px;
  color: var(--fv-text-3);
}

.intensity-advice {
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

.intensity-detail summary {
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

.detail-tag {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--fv-success) 16%, var(--fv-surface-2));
  color: var(--fv-success);
}

.detail-tag.warn {
  background: color-mix(in srgb, var(--fv-danger) 16%, var(--fv-surface-2));
  color: var(--fv-danger);
}

.intensity-empty {
  padding: 14px;
  border-radius: var(--fv-radius-sm);
  background: var(--fv-surface-2);
}

.intensity-empty p {
  margin: 0;
  font-size: 13px;
  color: var(--fv-text-2);
}
</style>

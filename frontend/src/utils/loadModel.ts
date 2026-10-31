/**
 * 训练负荷模型的展示层解析。
 *
 * 后端 `utils/readiness.py` 返回的 `readiness` 字段形态可能随版本变化（老接口没有
 * 负荷模型，离线时整个字段缺失），所以这里统一做一次"类型收窄 + 单位格式化"，
 * 首页与成长页共用同一套口径，避免出现两处文案不一致。
 */

/** 后端负荷模型（只声明 UI 真正用到的字段，其余透传）。 */
export interface LoadModel {
  acwr: number
  fitness: number
  fatigue: number
  tsb: number
  monotony: number
  strain: number
  form_trend: number
  rest_days: number
  weekly_load: number
  weekly_loads: number[]
  acute_load: number
  chronic_load: number
  intensity: string
  volume_multiplier: number
  reasons: string[]
}

/** ACWR 甜蜜区与可视化进度条的取值区间。 */
export const ACWR_SWEET_LOW = 0.8
export const ACWR_SWEET_HIGH = 1.3
export const ACWR_DANGER = 1.5

export const ACWR_SCALE_MIN = 0.5
export const ACWR_SCALE_MAX = 2.0

export type AcwrTone = 'ok' | 'watch' | 'risk'

const INTENSITY_LABELS: Record<string, string> = {
  rest: '主动恢复',
  light: '低强度',
  moderate: '中等强度',
  hard: '高强度',
}

function toNumber(value: unknown): number | null {
  // `Number(null)` 是 0、`Number('')` 也是 0，会把"缺失"误当成 0，这里先挡掉。
  if (value === null || value === undefined || value === '') return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

/**
 * 把接口返回的原始对象收窄成 `LoadModel`。
 * 缺少 `acwr`（老接口 / 离线）时返回 null，调用方据此隐藏负荷模块。
 */
export function parseLoadModel(raw: unknown): LoadModel | null {
  if (!raw || typeof raw !== 'object') return null
  const source = raw as Record<string, unknown>
  if (toNumber(source.acwr) === null) return null

  const weeklyLoads = Array.isArray(source.weekly_loads)
    ? source.weekly_loads.map(toNumber).filter((v): v is number => v !== null)
    : []
  const reasons = Array.isArray(source.reasons)
    ? source.reasons.filter((item): item is string => typeof item === 'string')
    : []

  return {
    acwr: toNumber(source.acwr) as number,
    fitness: toNumber(source.fitness) ?? 0,
    fatigue: toNumber(source.fatigue) ?? 0,
    tsb: toNumber(source.tsb) ?? 0,
    monotony: toNumber(source.monotony) ?? 0,
    strain: toNumber(source.strain) ?? 0,
    form_trend: toNumber(source.form_trend) ?? 0,
    rest_days: toNumber(source.rest_days) ?? -1,
    weekly_load: toNumber(source.weekly_load) ?? 0,
    weekly_loads: weeklyLoads,
    acute_load: toNumber(source.acute_load) ?? 0,
    chronic_load: toNumber(source.chronic_load) ?? 0,
    intensity: typeof source.intensity === 'string' ? source.intensity : '',
    volume_multiplier: toNumber(source.volume_multiplier) ?? 1,
    reasons,
  }
}

export function formatNumber(value: number, digits = 1): string {
  return Number.isFinite(value) ? value.toFixed(digits) : '—'
}

export function acwrText(model: LoadModel | null): string {
  return model ? formatNumber(model.acwr, 2) : '—'
}

export function acwrTone(model: LoadModel | null): AcwrTone {
  if (!model) return 'ok'
  if (model.acwr >= ACWR_DANGER) return 'risk'
  if (model.acwr > ACWR_SWEET_HIGH || model.acwr < ACWR_SWEET_LOW) return 'watch'
  return 'ok'
}

/** 把 0.5–2.0 的负荷比映射到区间条上的百分比位置。 */
export function acwrPercent(model: LoadModel | null): number {
  if (!model) return 0
  const span = ACWR_SCALE_MAX - ACWR_SCALE_MIN
  return Math.max(0, Math.min(100, ((model.acwr - ACWR_SCALE_MIN) / span) * 100))
}

/** TSB（体能 − 疲劳）的人话版本。 */
export function tsbText(model: LoadModel | null): string {
  if (!model) return '—'
  const rounded = Math.round(model.tsb)
  if (rounded > 0) return `体能 +${rounded}`
  if (rounded < 0) return `疲劳 ${rounded}`
  return '平衡'
}

export function restText(model: LoadModel | null): string {
  if (!model) return '—'
  const days = model.rest_days
  if (days < 0) return '暂无记录'
  if (days === 0) return '今天已练'
  return `${days} 天前`
}

export function intensityText(model: LoadModel | null): string {
  const key = model?.intensity ?? ''
  return INTENSITY_LABELS[key] ?? '按计划'
}

export function trendText(model: LoadModel | null): string {
  if (!model) return '—'
  const value = model.form_trend
  if (value > 0.3) return `+${formatNumber(value)} / 次`
  if (value < -0.3) return `${formatNumber(value)} / 次`
  return '持平'
}

export function volumeText(model: LoadModel | null): string {
  if (!model) return '—'
  return `${Math.round(model.volume_multiplier * 100)}%`
}

/**
 * 把周负荷序列归一化成 0–100 的柱高，用于纯 CSS / SVG 柱状图。
 * 全零序列返回全 0，避免除零。
 */
export function weeklyBars(loads: readonly number[]): number[] {
  if (loads.length === 0) return []
  const peak = Math.max(...loads)
  if (peak <= 0) return loads.map(() => 0)
  return loads.map((value) => Math.round((Math.max(0, value) / peak) * 100))
}

/**
 * 训练容量（Volume）的展示层。
 *
 * 后端 `utils/volume.py` 负责强度加权、有效容量、容量集中度与稳健趋势，
 * 这一层只做载荷收窄与文案，让「分析」页能直接展示
 * "我的容量够不够、结构均不均衡、趋势在涨还是在跌"。
 */

export interface VolumeMuscle {
  muscle: string
  label: string
  sets: number
  weeks: number
  tonnage: number
  intensity_volume: number
  effective_volume: number
  share: number
  status: 'low' | 'ok' | 'high' | 'unknown'
}

export interface VolumeSession {
  date: string
  sets: number
  measurable_sets: number
  tonnage: number
  intensity_volume: number
  effective_volume: number
}

export interface VolumeWeek {
  year: number
  week: number
  sessions: number
  sets: number
  measurable_sets: number
  tonnage: number
  intensity_volume: number
  effective_volume: number
}

export interface VolumePayload {
  available: boolean
  reason: string
  days: number
  weeks: number
  sessions: VolumeSession[]
  weekly: VolumeWeek[]
  muscles: VolumeMuscle[]
  total_tonnage: number
  total_intensity_volume: number
  total_effective_volume: number
  concentration: number
  trend: 'rising' | 'falling' | 'steady' | 'unknown'
  trend_slope: number
  verdict: string
  advice: string[]
}

/** 趋势 key → 展示色调。 */
export const TREND_TONE: Record<string, 'up' | 'flat' | 'down' | 'none'> = {
  rising: 'up',
  falling: 'down',
  steady: 'flat',
  unknown: 'none',
}

/** 趋势 key → 中文标签。 */
export const TREND_LABEL: Record<string, string> = {
  rising: '稳步上升',
  falling: '有所下滑',
  steady: '基本持平',
  unknown: '数据不足',
}

/** 肌群容量状态 → 中文标签。 */
export const MUSCLE_STATUS_LABEL: Record<string, string> = {
  low: '偏低',
  ok: '正常',
  high: '偏高',
  unknown: '未知',
}

function toNumber(value: unknown): number | null {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

function toText(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

function toTextList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []
}

export function trendTone(key: string | null | undefined): 'up' | 'flat' | 'down' | 'none' {
  const name = typeof key === 'string' ? key : ''
  return TREND_TONE[name] ?? 'none'
}

export function trendLabel(key: string | null | undefined, fallback?: string): string {
  const name = typeof key === 'string' ? key : ''
  if (fallback) return fallback
  return TREND_LABEL[name] ?? (name || '—')
}

export function muscleStatusLabel(status: string | null | undefined): string {
  const name = typeof status === 'string' ? status : ''
  return MUSCLE_STATUS_LABEL[name] ?? '未知'
}

export function parseVolumeMuscle(raw: unknown): VolumeMuscle | null {
  if (!raw || typeof raw !== 'object') return null
  const source = raw as Record<string, unknown>
  const muscle = toText(source.muscle)
  if (!muscle) return null
  const status = toText(source.status)
  return {
    muscle,
    label: toText(source.label) || muscle,
    sets: toNumber(source.sets) ?? 0,
    weeks: toNumber(source.weeks) ?? 0,
    tonnage: toNumber(source.tonnage) ?? 0,
    intensity_volume: toNumber(source.intensity_volume) ?? 0,
    effective_volume: toNumber(source.effective_volume) ?? 0,
    share: toNumber(source.share) ?? 0,
    status:
      status === 'low' || status === 'ok' || status === 'high' || status === 'unknown'
        ? status
        : 'unknown',
  }
}

export function parseVolumeSession(raw: unknown): VolumeSession | null {
  if (!raw || typeof raw !== 'object') return null
  const source = raw as Record<string, unknown>
  return {
    date: toText(source.date),
    sets: toNumber(source.sets) ?? 0,
    measurable_sets: toNumber(source.measurable_sets) ?? 0,
    tonnage: toNumber(source.tonnage) ?? 0,
    intensity_volume: toNumber(source.intensity_volume) ?? 0,
    effective_volume: toNumber(source.effective_volume) ?? 0,
  }
}

export function parseVolumeWeek(raw: unknown): VolumeWeek | null {
  if (!raw || typeof raw !== 'object') return null
  const source = raw as Record<string, unknown>
  return {
    year: toNumber(source.year) ?? 0,
    week: toNumber(source.week) ?? 0,
    sessions: toNumber(source.sessions) ?? 0,
    sets: toNumber(source.sets) ?? 0,
    measurable_sets: toNumber(source.measurable_sets) ?? 0,
    tonnage: toNumber(source.tonnage) ?? 0,
    intensity_volume: toNumber(source.intensity_volume) ?? 0,
    effective_volume: toNumber(source.effective_volume) ?? 0,
  }
}

export function parseVolume(raw: unknown): VolumePayload | null {
  if (!raw || typeof raw !== 'object') return null
  const source = raw as Record<string, unknown>
  const sessions = Array.isArray(source.sessions)
    ? source.sessions.map(parseVolumeSession).filter((item): item is VolumeSession => item !== null)
    : []
  const weekly = Array.isArray(source.weekly)
    ? source.weekly.map(parseVolumeWeek).filter((item): item is VolumeWeek => item !== null)
    : []
  const muscles = Array.isArray(source.muscles)
    ? source.muscles.map(parseVolumeMuscle).filter((item): item is VolumeMuscle => item !== null)
    : []
  const trend = toText(source.trend)
  return {
    available: Boolean(source.available),
    reason: toText(source.reason),
    days: toNumber(source.days) ?? 0,
    weeks: toNumber(source.weeks) ?? 0,
    sessions,
    weekly,
    muscles,
    total_tonnage: toNumber(source.total_tonnage) ?? 0,
    total_intensity_volume: toNumber(source.total_intensity_volume) ?? 0,
    total_effective_volume: toNumber(source.total_effective_volume) ?? 0,
    concentration: toNumber(source.concentration) ?? 0,
    trend:
      trend === 'rising' || trend === 'falling' || trend === 'steady' || trend === 'unknown'
        ? trend
        : 'unknown',
    trend_slope: toNumber(source.trend_slope) ?? 0,
    verdict: toText(source.verdict) || '数据不足',
    advice: toTextList(source.advice),
  }
}

/** 集中度（0–1）转成一句人话。 */
export function concentrationLabel(value: number): string {
  if (!Number.isFinite(value) || value <= 0) return '容量分布很集中'
  if (value >= 0.85) return '容量几乎全在一个部位'
  if (value >= 0.55) return '容量分布明显不均'
  if (value >= 0.3) return '容量分布略集中'
  return '容量分布均衡'
}

/** 有效容量的友好单位：超过一万显示为「万」。 */
export function formatVolume(value: number): string {
  if (!Number.isFinite(value) || value <= 0) return '0'
  if (value >= 10000) return `${(value / 10000).toFixed(1)} 万`
  return Math.round(value).toLocaleString('zh-CN')
}

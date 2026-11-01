/**
 * 训练强度分布（TRIMP）的展示层。
 *
 * 后端 `utils/trimp.py` 负责强度区间划分、负荷计算与平衡判定，这一层只做
 * 载荷收窄与文案，让「分析」页能直接展示"我的高强度组是不是练太多了"。
 */

export interface IntensityZone {
  key: string
  label: string
  sets: number
  share: number
  target_share: number
  deviation: number
  load: number
}

export interface IntensitySession {
  date: string
  sets: number
  zones: IntensityZone[]
  rpe_trimp: number
  intensity_trimp: number
  high_intensity_sets: number
  balanced: boolean
  notes: string[]
}

export interface IntensityWeek {
  year: number
  week: number
  sessions: number
  sets: number
  zones: { key: string; label: string; sets: number; share: number }[]
  rpe_trimp: number
  intensity_trimp: number
  high_intensity_sets: number
  high_intensity_days: number
  over_high_intensity_cap: boolean
}

export interface IntensityPayload {
  available: boolean
  reason: string
  days: number
  weeks: number
  sessions: IntensitySession[]
  weekly: IntensityWeek[]
  balance_score: number
  verdict: string
  advice: string[]
}

/** 强度区间 key → 展示色调。与后端的 ZONE_BOUNDS 一一对应。 */
export const ZONE_TONE: Record<string, 'calm' | 'steady' | 'warm' | 'hot'> = {
  zone_1: 'calm',
  zone_2: 'steady',
  zone_3: 'warm',
  zone_4: 'hot',
}

/** 强度区间的默认中文名，后端没给 label 时兜底。 */
export const ZONE_LABEL: Record<string, string> = {
  zone_1: '恢复',
  zone_2: '基础',
  zone_3: '发展',
  zone_4: '强度',
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

export function zoneTone(key: string | null | undefined): 'calm' | 'steady' | 'warm' | 'hot' {
  const name = typeof key === 'string' ? key : ''
  return ZONE_TONE[name] ?? 'calm'
}

export function zoneLabel(key: string | null | undefined, fallback?: string): string {
  const name = typeof key === 'string' ? key : ''
  if (fallback) return fallback
  return ZONE_LABEL[name] ?? (name || '—')
}

export function parseIntensityZone(raw: unknown): IntensityZone | null {
  if (!raw || typeof raw !== 'object') return null
  const source = raw as Record<string, unknown>
  const key = toText(source.key)
  if (!key) return null
  return {
    key,
    label: zoneLabel(key, toText(source.label)),
    sets: toNumber(source.sets) ?? 0,
    share: toNumber(source.share) ?? 0,
    target_share: toNumber(source.target_share) ?? 0,
    deviation: toNumber(source.deviation) ?? 0,
    load: toNumber(source.load) ?? 0,
  }
}

export function parseIntensitySession(raw: unknown): IntensitySession | null {
  if (!raw || typeof raw !== 'object') return null
  const source = raw as Record<string, unknown>
  const zones = Array.isArray(source.zones)
    ? source.zones.map(parseIntensityZone).filter((item): item is IntensityZone => item !== null)
    : []
  return {
    date: toText(source.date),
    sets: toNumber(source.sets) ?? zones.reduce((sum, item) => sum + item.sets, 0),
    zones,
    rpe_trimp: toNumber(source.rpe_trimp) ?? 0,
    intensity_trimp: toNumber(source.intensity_trimp) ?? 0,
    high_intensity_sets: toNumber(source.high_intensity_sets) ?? 0,
    balanced: Boolean(source.balanced),
    notes: toTextList(source.notes),
  }
}

export function parseIntensityWeek(raw: unknown): IntensityWeek | null {
  if (!raw || typeof raw !== 'object') return null
  const source = raw as Record<string, unknown>
  const zones = Array.isArray(source.zones)
    ? source.zones
        .map((item) => {
          if (!item || typeof item !== 'object') return null
          const entry = item as Record<string, unknown>
          const key = toText(entry.key)
          if (!key) return null
          return {
            key,
            label: zoneLabel(key, toText(entry.label)),
            sets: toNumber(entry.sets) ?? 0,
            share: toNumber(entry.share) ?? 0,
          }
        })
        .filter((item): item is { key: string; label: string; sets: number; share: number } => item !== null)
    : []
  return {
    year: toNumber(source.year) ?? 0,
    week: toNumber(source.week) ?? 0,
    sessions: toNumber(source.sessions) ?? 0,
    sets: toNumber(source.sets) ?? 0,
    zones,
    rpe_trimp: toNumber(source.rpe_trimp) ?? 0,
    intensity_trimp: toNumber(source.intensity_trimp) ?? 0,
    high_intensity_sets: toNumber(source.high_intensity_sets) ?? 0,
    high_intensity_days: toNumber(source.high_intensity_days) ?? 0,
    over_high_intensity_cap: Boolean(source.over_high_intensity_cap),
  }
}

export function parseIntensity(raw: unknown): IntensityPayload | null {
  if (!raw || typeof raw !== 'object') return null
  const source = raw as Record<string, unknown>
  const sessions = Array.isArray(source.sessions)
    ? source.sessions
        .map(parseIntensitySession)
        .filter((item): item is IntensitySession => item !== null)
    : []
  const weekly = Array.isArray(source.weekly)
    ? source.weekly.map(parseIntensityWeek).filter((item): item is IntensityWeek => item !== null)
    : []
  return {
    available: Boolean(source.available),
    reason: toText(source.reason),
    days: toNumber(source.days) ?? 0,
    weeks: toNumber(source.weeks) ?? 0,
    sessions,
    weekly,
    balance_score: toNumber(source.balance_score) ?? 0,
    verdict: toText(source.verdict) || '数据不足',
    advice: toTextList(source.advice),
  }
}

/** 平衡分（0–1）转成一句人话。 */
export function balanceLabel(score: number): string {
  if (!Number.isFinite(score) || score <= 0) return '还没有足够数据'
  if (score >= 0.9) return '强度分布很均衡'
  if (score >= 0.75) return '强度分布基本合理'
  if (score >= 0.6) return '强度分布轻度失衡'
  return '强度分布明显失衡'
}

/** 某个强度区间的占比文案，例如「强度 20%」。 */
export function zoneShareText(zone: IntensityZone): string {
  return `${zone.label} ${Math.round(zone.share * 100)}%`
}

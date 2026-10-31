/**
 * 分肌群恢复模型的展示层。
 *
 * 后端 `utils/recovery.py` 负责算，这一层只负责把 API 载荷收窄成安全类型、补上
 * 文案与配色，让多个页面（训练页 / 首页 / 成长页）共用同一套口径。
 */

export type MuscleStatus = 'ready' | 'caution' | 'fatigued'
export type VolumeStatus = 'under' | 'optimal' | 'over' | 'idle'

export interface MuscleRecoveryState {
  muscle: string
  label: string
  residual: number
  recovery: number
  status: MuscleStatus
  hours_to_ready: number
  weekly_sets: number
  volume_status: VolumeStatus
  multiplier: number
}

export interface MuscleRecoveryPayload {
  muscles: MuscleRecoveryState[]
  focus: string[]
  avoid: string[]
}

/** 与后端 `READY_THRESHOLD` / `FATIGUED_THRESHOLD` 保持一致。 */
export const READY_THRESHOLD = 85
export const FATIGUED_THRESHOLD = 60

const STATUSES: MuscleStatus[] = ['ready', 'caution', 'fatigued']
const VOLUME_STATUSES: VolumeStatus[] = ['under', 'optimal', 'over', 'idle']

const STATUS_LABELS: Record<MuscleStatus, string> = {
  ready: '已恢复',
  caution: '恢复中',
  fatigued: '酸痛中',
}

const VOLUME_HINTS: Record<VolumeStatus, string> = {
  under: '本周容量偏低',
  optimal: '本周容量合适',
  over: '本周容量偏多',
  idle: '本周还没练',
}

function toNumber(value: unknown): number | null {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

function toStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  return value.filter((item): item is string => typeof item === 'string')
}

export function recoveryStatus(recovery: number | null | undefined): MuscleStatus {
  const value = toNumber(recovery)
  if (value === null) return 'ready'
  if (value >= READY_THRESHOLD) return 'ready'
  if (value >= FATIGUED_THRESHOLD) return 'caution'
  return 'fatigued'
}

export function statusLabel(status: MuscleStatus): string {
  return STATUS_LABELS[status] ?? '恢复中'
}

export function volumeHint(status: VolumeStatus): string {
  return VOLUME_HINTS[status] ?? ''
}

/** 距完全恢复还有多久：`已恢复` / `约 6 小时` / `约 2 天`。 */
export function hoursToReadyText(hours: number | null | undefined): string {
  const value = toNumber(hours)
  if (value === null || value <= 0) return '已恢复'
  if (value < 24) return `约 ${Math.round(value)} 小时`
  return `约 ${Math.round(value / 24)} 天`
}

/** 推荐加权 → 一句话解释，用于列表 hover 或推荐理由。 */
export function multiplierHint(multiplier: number | null | undefined): string {
  const value = toNumber(multiplier)
  if (value === null) return ''
  if (value >= 1.08) return '状态正好，适合加量'
  if (value >= 0.95) return '可以正常训练'
  if (value >= 0.8) return '建议降低容量'
  return '仍在酸痛，尽量避开'
}

export function parseMuscleState(raw: unknown): MuscleRecoveryState | null {
  if (!raw || typeof raw !== 'object') return null
  const source = raw as Record<string, unknown>

  const muscle = source.muscle
  if (typeof muscle !== 'string' || !muscle) return null

  const recovery = toNumber(source.recovery) ?? 100
  const status = source.status
  return {
    muscle,
    label: typeof source.label === 'string' && source.label ? source.label : muscle,
    residual: toNumber(source.residual) ?? 0,
    recovery: Math.max(0, Math.min(100, recovery)),
    status: STATUSES.includes(status as MuscleStatus)
      ? (status as MuscleStatus)
      : recoveryStatus(recovery),
    hours_to_ready: toNumber(source.hours_to_ready) ?? 0,
    weekly_sets: toNumber(source.weekly_sets) ?? 0,
    volume_status: VOLUME_STATUSES.includes(source.volume_status as VolumeStatus)
      ? (source.volume_status as VolumeStatus)
      : 'idle',
    multiplier: toNumber(source.multiplier) ?? 1,
  }
}

/**
 * 收窄后端 `/growth/muscle-recovery/` 的载荷。
 * 字段缺失或类型不对时返回 null，让调用方整块隐藏，而不是渲染出半截 UI。
 */
export function parseMuscleRecovery(raw: unknown): MuscleRecoveryPayload | null {
  if (!raw || typeof raw !== 'object') return null
  const source = raw as Record<string, unknown>
  if (!Array.isArray(source.muscles)) return null

  const muscles = source.muscles
    .map(parseMuscleState)
    .filter((item): item is MuscleRecoveryState => item !== null)
  if (muscles.length === 0) return null

  return {
    muscles,
    focus: toStringArray(source.focus),
    avoid: toStringArray(source.avoid),
  }
}

/** 按恢复度升序：最酸痛的排最前，方便一眼看到"今天别练什么"。 */
export function sortByFatigue(states: readonly MuscleRecoveryState[]): MuscleRecoveryState[] {
  return [...states].sort((a, b) => a.recovery - b.recovery)
}

export function labelsFor(states: readonly MuscleRecoveryState[], keys: readonly string[]): string[] {
  const lookup = new Map(states.map((state) => [state.muscle, state.label]))
  return keys.map((key) => lookup.get(key) ?? key)
}

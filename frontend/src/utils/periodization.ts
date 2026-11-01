/**
 * 训练周期化（mesocycle）的展示层。
 *
 * 后端 `utils/periodization.py` 负责阶段划分、容量分配与重量处方，这一层只做
 * 载荷收窄与文案，让"分析"页与"训练"页共用同一套口径。
 */

export interface MesocycleExercise {
  exercise_id: number
  name: string
  sets: number
  reps: number
  weight: number
  e1rm: number
  based_on_e1rm: boolean
  equipment: string
  note: string
}

export interface MesocycleSlot {
  muscle: string
  label: string
  sets: number
  reps: number
  weight: number
  e1rm: number
  based_on_e1rm: boolean
  note: string
  exercises: MesocycleExercise[]
}

export interface MesocycleSession {
  index: number
  label: string
  focus: string[]
  slots: MesocycleSlot[]
  total_sets: number
}

export interface MesocycleWeek {
  index: number
  phase: string
  label: string
  note: string
  volume: number
  intensity: number
  reps_low: number
  reps_high: number
  rir: number
  total_sets: number
  sessions: MesocycleSession[]
}

export interface MesocyclePayload {
  weeks: MesocycleWeek[]
  days_per_week: number
  readiness: number
  focus: string[]
  avoid: string[]
  autoregulation: number
  notes: string[]
  total_weeks: number
  total_sets: number
}

/** 阶段 key → 中文名与视觉色调。 */
export const PHASE_META: Record<string, { label: string; tone: 'build' | 'intense' | 'peak' | 'rest' }> = {
  accumulation: { label: '积累', tone: 'build' },
  intensification: { label: '强化', tone: 'intense' },
  realization: { label: '实现', tone: 'peak' },
  deload: { label: '减量', tone: 'rest' },
}

function toNumber(value: unknown): number | null {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

export function phaseLabel(phase: string | null | undefined): string {
  const key = typeof phase === 'string' ? phase : ''
  return PHASE_META[key]?.label ?? (key || '—')
}

export function phaseTone(phase: string | null | undefined): 'build' | 'intense' | 'peak' | 'rest' {
  const key = typeof phase === 'string' ? phase : ''
  return PHASE_META[key]?.tone ?? 'build'
}

export function parseMesocycleExercise(raw: unknown): MesocycleExercise | null {
  if (!raw || typeof raw !== 'object') return null
  const source = raw as Record<string, unknown>
  const exerciseId = toNumber(source.exercise_id)
  if (exerciseId === null) return null
  return {
    exercise_id: exerciseId,
    name: typeof source.name === 'string' && source.name ? source.name : `动作 #${exerciseId}`,
    sets: toNumber(source.sets) ?? 0,
    reps: toNumber(source.reps) ?? 0,
    weight: toNumber(source.weight) ?? 0,
    e1rm: toNumber(source.e1rm) ?? 0,
    based_on_e1rm: Boolean(source.based_on_e1rm),
    equipment: typeof source.equipment === 'string' ? source.equipment : '',
    note: typeof source.note === 'string' ? source.note : '',
  }
}

export function parseMesocycleSlot(raw: unknown): MesocycleSlot | null {
  if (!raw || typeof raw !== 'object') return null
  const source = raw as Record<string, unknown>
  const muscle = typeof source.muscle === 'string' ? source.muscle : ''
  if (!muscle) return null
  return {
    muscle,
    label: typeof source.label === 'string' && source.label ? source.label : muscle,
    sets: toNumber(source.sets) ?? 0,
    reps: toNumber(source.reps) ?? 0,
    weight: toNumber(source.weight) ?? 0,
    e1rm: toNumber(source.e1rm) ?? 0,
    based_on_e1rm: Boolean(source.based_on_e1rm),
    note: typeof source.note === 'string' ? source.note : '',
    exercises: Array.isArray(source.exercises)
      ? source.exercises
          .map(parseMesocycleExercise)
          .filter((item): item is MesocycleExercise => item !== null)
      : [],
  }
}

export function parseMesocycleSession(raw: unknown): MesocycleSession | null {
  if (!raw || typeof raw !== 'object') return null
  const source = raw as Record<string, unknown>
  const slots = Array.isArray(source.slots)
    ? source.slots.map(parseMesocycleSlot).filter((item): item is MesocycleSlot => item !== null)
    : []
  const focus = Array.isArray(source.focus)
    ? source.focus.filter((item): item is string => typeof item === 'string')
    : []
  return {
    index: toNumber(source.index) ?? 0,
    label: typeof source.label === 'string' && source.label ? source.label : '训练日',
    focus,
    slots,
    total_sets: toNumber(source.total_sets) ?? slots.reduce((sum, item) => sum + item.sets, 0),
  }
}

export function parseMesocycleWeek(raw: unknown): MesocycleWeek | null {
  if (!raw || typeof raw !== 'object') return null
  const source = raw as Record<string, unknown>
  const sessions = Array.isArray(source.sessions)
    ? source.sessions
        .map(parseMesocycleSession)
        .filter((item): item is MesocycleSession => item !== null)
    : []
  const phase = typeof source.phase === 'string' ? source.phase : ''
  return {
    index: toNumber(source.index) ?? 0,
    phase,
    label: typeof source.label === 'string' && source.label ? source.label : phaseLabel(phase),
    note: typeof source.note === 'string' ? source.note : '',
    volume: toNumber(source.volume) ?? 1,
    intensity: toNumber(source.intensity) ?? 0,
    reps_low: toNumber(source.reps_low) ?? 0,
    reps_high: toNumber(source.reps_high) ?? 0,
    rir: toNumber(source.rir) ?? 0,
    total_sets:
      toNumber(source.total_sets) ?? sessions.reduce((sum, item) => sum + item.total_sets, 0),
    sessions,
  }
}

export function parseMesocycle(raw: unknown): MesocyclePayload | null {
  if (!raw || typeof raw !== 'object') return null
  const source = raw as Record<string, unknown>
  if (!Array.isArray(source.weeks)) return null

  const weeks = source.weeks
    .map(parseMesocycleWeek)
    .filter((item): item is MesocycleWeek => item !== null)

  const stringList = (value: unknown): string[] =>
    Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []

  return {
    weeks,
    days_per_week: toNumber(source.days_per_week) ?? 0,
    readiness: toNumber(source.readiness) ?? 0,
    focus: stringList(source.focus),
    avoid: stringList(source.avoid),
    autoregulation: toNumber(source.autoregulation) ?? 1,
    notes: stringList(source.notes),
    total_weeks: toNumber(source.total_weeks) ?? weeks.length,
    total_sets:
      toNumber(source.total_sets) ?? weeks.reduce((sum, item) => sum + item.total_sets, 0),
  }
}

/** 单个安排的展示文案：`4 组 × 8 次 · 62.5 kg`。 */
export function slotText(slot: MesocycleSlot): string {
  const reps = slot.reps > 0 ? ` × ${slot.reps} 次` : ''
  const weight = slot.weight > 0 ? ` · ${slot.weight} kg` : ''
  return `${slot.sets} 组${reps}${weight}`
}

/** 单个动作的展示文案：`杠铃卧推 3 组 × 8 次 · 62.5 kg`。 */
export function exerciseText(exercise: MesocycleExercise): string {
  const reps = exercise.reps > 0 ? ` × ${exercise.reps} 次` : ''
  const weight = exercise.weight > 0 ? ` · ${exercise.weight} kg` : ''
  return `${exercise.name} ${exercise.sets} 组${reps}${weight}`
}

/** 容量系数 → 一句话说明。 */
export function volumeHint(volume: number | null | undefined): string {
  const value = toNumber(volume)
  if (value === null) return '容量 —'
  const percent = Math.round(value * 100)
  if (percent >= 95) return '容量满载'
  if (percent >= 80) return '容量较高'
  if (percent >= 60) return '容量中等'
  return '容量收缩'
}

/** 强度系数 → 一句话说明。 */
export function intensityHint(intensity: number | null | undefined): string {
  const value = toNumber(intensity)
  if (value === null || value <= 0) return '强度 —'
  return `强度 ${Math.round(value * 100)}%`
}

/** 准备度折扣文案。 */
export function autoregulationText(factor: number | null | undefined): string {
  const value = toNumber(factor)
  if (value === null || value >= 0.999) return '容量正常'
  return `容量下调 ${Math.round((1 - value) * 100)}%`
}

/** 找出总组数最多的一周。 */
export function heaviestWeek(weeks: readonly MesocycleWeek[]): MesocycleWeek | null {
  if (weeks.length === 0) return null
  return weeks.reduce((best, item) => (item.total_sets > best.total_sets ? item : best), weeks[0]!)
}

/** 找出减量周（阶段 key 为 deload）。 */
export function deloadWeek(weeks: readonly MesocycleWeek[]): MesocycleWeek | null {
  return weeks.find((item) => item.phase === 'deload') ?? null
}

/**
 * 力量曲线的展示层。
 *
 * 后端 `utils/strength.py` 负责算 e1RM、趋势与处方，这一层只做载荷收窄与文案，
 * 让数据中心与训练页共用同一套口径。
 */

export interface StrengthPoint {
  date: string
  e1rm: number
  weight: number
  reps: number
  method: string
}

export interface StrengthSummary {
  latest: number
  best: number
  trend: number
  trend_percent: number
  sessions: number
  first_session: string | null
  deload: {
    deload: boolean
    factor: number
    reasons: string[]
    advice: string
  }
}

export interface StrengthExercise {
  exercise_id: number
  name: string
  target_muscle: string
  e1rm: number
  best: number
  trend: number
  points: StrengthPoint[]
  summary: StrengthSummary
}

export interface StrengthPrescription {
  available: boolean
  reason?: string
  exercise_id?: number
  name?: string
  e1rm?: number
  weight?: number
  target_reps?: number
  target_rir?: number
  changed?: boolean
  advice?: string
}

export interface StrengthPayload {
  days: number
  exercises: StrengthExercise[]
  prescription: StrengthPrescription | null
}

function toNumber(value: unknown): number | null {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

export function parseStrengthPoint(raw: unknown): StrengthPoint | null {
  if (!raw || typeof raw !== 'object') return null
  const source = raw as Record<string, unknown>
  const e1rm = toNumber(source.e1rm)
  if (e1rm === null || e1rm <= 0) return null
  return {
    date: typeof source.date === 'string' ? source.date : '',
    e1rm,
    weight: toNumber(source.weight) ?? 0,
    reps: toNumber(source.reps) ?? 0,
    method: typeof source.method === 'string' ? source.method : 'rep_formula',
  }
}

export function parseStrengthSummary(raw: unknown): StrengthSummary {
  const source = (raw ?? {}) as Record<string, unknown>
  const deloadRaw = (source.deload ?? {}) as Record<string, unknown>
  const reasons = Array.isArray(deloadRaw.reasons)
    ? deloadRaw.reasons.filter((item): item is string => typeof item === 'string')
    : []
  return {
    latest: toNumber(source.latest) ?? 0,
    best: toNumber(source.best) ?? 0,
    trend: toNumber(source.trend) ?? 0,
    trend_percent: toNumber(source.trend_percent) ?? 0,
    sessions: toNumber(source.sessions) ?? 0,
    first_session: typeof source.first_session === 'string' ? source.first_session : null,
    deload: {
      deload: Boolean(deloadRaw.deload),
      factor: toNumber(deloadRaw.factor) ?? 1,
      reasons,
      advice: typeof deloadRaw.advice === 'string' ? deloadRaw.advice : '',
    },
  }
}

export function parseStrengthExercise(raw: unknown): StrengthExercise | null {
  if (!raw || typeof raw !== 'object') return null
  const source = raw as Record<string, unknown>
  const exerciseId = toNumber(source.exercise_id)
  if (exerciseId === null) return null

  const points = Array.isArray(source.points)
    ? source.points.map(parseStrengthPoint).filter((item): item is StrengthPoint => item !== null)
    : []

  return {
    exercise_id: exerciseId,
    name: typeof source.name === 'string' && source.name ? source.name : `动作 #${exerciseId}`,
    target_muscle: typeof source.target_muscle === 'string' ? source.target_muscle : '',
    e1rm: toNumber(source.e1rm) ?? 0,
    best: toNumber(source.best) ?? 0,
    trend: toNumber(source.trend) ?? 0,
    points,
    summary: parseStrengthSummary(source.summary),
  }
}

export function parseStrength(raw: unknown): StrengthPayload | null {
  if (!raw || typeof raw !== 'object') return null
  const source = raw as Record<string, unknown>
  if (!Array.isArray(source.exercises)) return null

  const exercises = source.exercises
    .map(parseStrengthExercise)
    .filter((item): item is StrengthExercise => item !== null)

  const prescriptionRaw = source.prescription
  const prescription =
    prescriptionRaw && typeof prescriptionRaw === 'object'
      ? ({
          available: Boolean((prescriptionRaw as Record<string, unknown>).available),
          reason:
            typeof (prescriptionRaw as Record<string, unknown>).reason === 'string'
              ? ((prescriptionRaw as Record<string, unknown>).reason as string)
              : undefined,
          exercise_id: toNumber((prescriptionRaw as Record<string, unknown>).exercise_id) ?? undefined,
          name:
            typeof (prescriptionRaw as Record<string, unknown>).name === 'string'
              ? ((prescriptionRaw as Record<string, unknown>).name as string)
              : undefined,
          e1rm: toNumber((prescriptionRaw as Record<string, unknown>).e1rm) ?? undefined,
          weight: toNumber((prescriptionRaw as Record<string, unknown>).weight) ?? undefined,
          target_reps: toNumber((prescriptionRaw as Record<string, unknown>).target_reps) ?? undefined,
          target_rir: toNumber((prescriptionRaw as Record<string, unknown>).target_rir) ?? undefined,
          changed: Boolean((prescriptionRaw as Record<string, unknown>).changed),
          advice:
            typeof (prescriptionRaw as Record<string, unknown>).advice === 'string'
              ? ((prescriptionRaw as Record<string, unknown>).advice as string)
              : undefined,
        } as StrengthPrescription)
      : null

  return {
    days: toNumber(source.days) ?? 0,
    exercises,
    prescription,
  }
}

/** 趋势描述：上升 / 持平 / 回落。 */
export function trendText(trend: number | null | undefined): string {
  const value = toNumber(trend)
  if (value === null || Math.abs(value) < 0.15) return '持平'
  return value > 0 ? '上升' : '回落'
}

export function trendType(trend: number | null | undefined): 'up' | 'flat' | 'down' {
  const value = toNumber(trend)
  if (value === null || Math.abs(value) < 0.15) return 'flat'
  return value > 0 ? 'up' : 'down'
}

/** e1RM 的展示：整数直接显示，一位小数保留。 */
export function formatE1rm(value: number | null | undefined): string {
  const parsed = toNumber(value)
  if (parsed === null || parsed <= 0) return '—'
  return Number.isInteger(parsed) ? String(parsed) : parsed.toFixed(1)
}

/** 处方文案：`下次建议 82.5 kg × 6 次（保留 2 次余量）`。 */
export function prescriptionText(prescription: StrengthPrescription | null | undefined): string {
  if (!prescription || !prescription.available) {
    return prescription?.reason ?? '还没有足够的负重训练数据'
  }
  const weight = toNumber(prescription.weight) ?? 0
  const reps = toNumber(prescription.target_reps) ?? 0
  const rir = toNumber(prescription.target_rir) ?? 0
  if (weight <= 0) return '暂时没有可用的处方'
  return `下次建议 ${weight} kg × ${reps} 次（保留 ${rir} 次余量）`
}

/** 只保留有训练点的动作，按历史最好 e1RM 降序。 */
export function exercisesWithData(exercises: readonly StrengthExercise[]): StrengthExercise[] {
  return exercises.filter((item) => item.points.length > 0).sort((a, b) => b.best - a.best)
}

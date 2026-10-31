/**
 * Period aggregation for training sessions.
 *
 * Pure and dependency-free so the numbers shown in the UI can be unit tested.
 */
export interface SessionLike {
  start_time: string
  end_time: string | null
  is_completed: boolean
  calories_burned: number
  performance_score: number
}

export interface DateWindow {
  start: Date
  end: Date
}

export interface PeriodStats {
  count: number
  completed: number
  minutes: number
  calories: number
  avgScore: number
}

const startOfDay = (date: Date): Date => {
  const copy = new Date(date)
  copy.setHours(0, 0, 0, 0)
  return copy
}

const endOfDay = (date: Date): Date => {
  const copy = new Date(date)
  copy.setHours(23, 59, 59, 999)
  return copy
}

const addDays = (date: Date, days: number): Date => {
  const copy = new Date(date)
  copy.setDate(copy.getDate() + days)
  return copy
}

/**
 * Inclusive windows for the trailing 7 days (including today) and the
 * calendar month containing `reference`.
 */
export const periodWindows = (reference: Date = new Date()): {
  week: DateWindow
  month: DateWindow
} => {
  const dayStart = startOfDay(reference)
  return {
    week: { start: addDays(dayStart, -6), end: endOfDay(dayStart) },
    month: {
      start: startOfDay(new Date(reference.getFullYear(), reference.getMonth(), 1)),
      end: endOfDay(reference),
    },
  }
}

/** Filters sessions whose start time falls inside the inclusive window. */
export const sessionsWithin = <T extends SessionLike>(
  sessions: readonly T[],
  window: DateWindow,
): T[] =>
  sessions.filter((session) => {
    const started = new Date(session.start_time)
    return started >= window.start && started <= window.end
  })

/** Duration in minutes; a session still running contributes 0. */
export const sessionMinutes = (session: SessionLike): number => {
  if (!session.end_time) return 0
  const ms = new Date(session.end_time).getTime() - new Date(session.start_time).getTime()
  if (!Number.isFinite(ms) || ms <= 0) return 0
  return Math.round(ms / 60000)
}

/** Aggregates sessions into the headline counters shown in the UI. */
export const aggregate = (sessions: readonly SessionLike[]): PeriodStats => {
  let minutes = 0
  let calories = 0
  let scoreSum = 0
  let scored = 0

  for (const session of sessions) {
    minutes += sessionMinutes(session)
    calories += Number(session.calories_burned) || 0
    const score = Number(session.performance_score) || 0
    if (score > 0) {
      scoreSum += score
      scored += 1
    }
  }

  return {
    count: sessions.length,
    completed: sessions.filter((session) => session.is_completed).length,
    minutes,
    calories: Math.round(calories),
    avgScore: scored > 0 ? Math.round(scoreSum / scored) : 0,
  }
}

/** Week and month summaries in one call, defaulting to "now". */
export const periodSummaries = (
  sessions: readonly SessionLike[],
  reference: Date = new Date(),
): { week: PeriodStats; month: PeriodStats } => {
  const windows = periodWindows(reference)
  return {
    week: aggregate(sessionsWithin(sessions, windows.week)),
    month: aggregate(sessionsWithin(sessions, windows.month)),
  }
}

/** Local calendar day key (YYYY-MM-DD) used for streak maths. */
export const dayKey = (date: Date | string): string => {
  const value = typeof date === 'string' ? new Date(date) : date
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}`
}

/** Unique training days, earliest first. Exported for calendar views. */
export const trainingDays = (sessions: readonly SessionLike[]): string[] =>
  [...new Set(sessions.map((session) => dayKey(session.start_time)))].sort()

const gapInDays = (later: string, earlier: string): number =>
  Math.round(
    (new Date(`${later}T00:00:00`).getTime() - new Date(`${earlier}T00:00:00`).getTime()) /
      86400000,
  )

/** Longest run of consecutive training days. */
export const longestStreak = (sessions: readonly SessionLike[]): number => {
  const days = trainingDays(sessions)
  if (days.length === 0) return 0

  let best = 1
  let run = 1
  for (let i = 1; i < days.length; i += 1) {
    if (gapInDays(days[i]!, days[i - 1]!) === 1) {
      run += 1
      best = Math.max(best, run)
    } else {
      run = 1
    }
  }
  return best
}

/**
 * Days in a row counting back from the latest session. The streak only holds
 * when that session falls today or yesterday, so a missed day resets it.
 */
export const currentStreak = (
  sessions: readonly SessionLike[],
  today: Date = new Date(),
): number => {
  const days = trainingDays(sessions)
  if (days.length === 0) return 0

  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)
  const latest = days[days.length - 1]!
  if (latest !== dayKey(today) && latest !== dayKey(yesterday)) return 0

  let streak = 1
  for (let i = days.length - 1; i > 0; i -= 1) {
    if (gapInDays(days[i]!, days[i - 1]!) === 1) streak += 1
    else break
  }
  return streak
}

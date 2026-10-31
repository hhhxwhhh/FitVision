/**
 * Month-grid maths for the training calendar.
 *
 * Pure and timezone-free: callers pass an explicit year/month plus the set of
 * days that contain a session.
 */
export interface CalendarCell {
  /** Day of month, or null for padding cells outside the month. */
  day: number | null
  /** ISO key (YYYY-MM-DD) for the cell, useful for tooltips and keys. */
  key: string
  /** True when at least one session happened on this day. */
  active: boolean
  /** True when the cell belongs to the requested month. */
  inMonth: boolean
}

const pad = (value: number) => String(value).padStart(2, '0')

export const isoKey = (year: number, month: number, day: number): string =>
  `${year}-${pad(month)}-${pad(day)}`

/** Number of days in a month (1-12) for a given year. */
export const daysInMonth = (year: number, month: number): number =>
  new Date(year, month, 0).getDate()

/** Weekday index of the first day of the month, Monday-based (0-6). */
export const firstWeekday = (year: number, month: number): number => {
  const weekday = new Date(year, month - 1, 1).getDay() // 0 = Sunday
  return (weekday + 6) % 7
}

/**
 * Builds a Monday-first grid covering the month, padded with the surrounding
 * days so each row is a full week.
 */
export const buildMonthGrid = (
  year: number,
  month: number,
  activeDays: readonly string[] = [],
): CalendarCell[][] => {
  const active = new Set(activeDays)
  const total = daysInMonth(year, month)
  const lead = firstWeekday(year, month)

  const cells: CalendarCell[] = []

  // Leading days from the previous month.
  const prevMonth = month === 1 ? 12 : month - 1
  const prevYear = month === 1 ? year - 1 : year
  const prevTotal = daysInMonth(prevYear, prevMonth)
  for (let i = lead - 1; i >= 0; i -= 1) {
    const day = prevTotal - i
    cells.push({ day, key: isoKey(prevYear, prevMonth, day), active: active.has(isoKey(prevYear, prevMonth, day)), inMonth: false })
  }

  for (let day = 1; day <= total; day += 1) {
    const key = isoKey(year, month, day)
    cells.push({ day, key, active: active.has(key), inMonth: true })
  }

  // Trailing days to complete the final week.
  const nextMonth = month === 12 ? 1 : month + 1
  const nextYear = month === 12 ? year + 1 : year
  const remainder = cells.length % 7
  if (remainder !== 0) {
    for (let day = 1; day <= 7 - remainder; day += 1) {
      cells.push({
        day,
        key: isoKey(nextYear, nextMonth, day),
        active: active.has(isoKey(nextYear, nextMonth, day)),
        inMonth: false,
      })
    }
  }

  const weeks: CalendarCell[][] = []
  for (let i = 0; i < cells.length; i += 7) {
    weeks.push(cells.slice(i, i + 7))
  }
  return weeks
}

/** Counts active days inside a grid (used for the monthly summary line). */
export const countActiveInGrid = (weeks: readonly CalendarCell[][]): number =>
  weeks.reduce(
    (total, week) => total + week.filter((cell) => cell.inMonth && cell.active).length,
    0,
  )

import { describe, expect, it } from 'vitest'
import { buildMonthGrid, countActiveInGrid, daysInMonth, firstWeekday, isoKey } from './calendar'

describe('daysInMonth', () => {
  it('handles February in leap and common years', () => {
    expect(daysInMonth(2024, 2)).toBe(29)
    expect(daysInMonth(2026, 2)).toBe(28)
  })

  it('handles 30 and 31 day months', () => {
    expect(daysInMonth(2026, 4)).toBe(30)
    expect(daysInMonth(2026, 10)).toBe(31)
  })
})

describe('firstWeekday', () => {
  it('is Monday-based', () => {
    // 2026-06-01 is a Monday.
    expect(firstWeekday(2026, 6)).toBe(0)
    // 2026-10-01 is a Thursday.
    expect(firstWeekday(2026, 10)).toBe(3)
  })
})

describe('isoKey', () => {
  it('zero-pads month and day', () => {
    expect(isoKey(2026, 1, 5)).toBe('2026-01-05')
  })
})

describe('buildMonthGrid', () => {
  it('returns full weeks that cover the month', () => {
    const weeks = buildMonthGrid(2026, 10)
    expect(weeks.length).toBeGreaterThanOrEqual(5)
    for (const week of weeks) expect(week).toHaveLength(7)
  })

  it('marks only the requested month as in-month', () => {
    const weeks = buildMonthGrid(2026, 10)
    const inMonth = weeks.flat().filter((cell) => cell.inMonth)
    expect(inMonth).toHaveLength(31)
    expect(inMonth[0]!.day).toBe(1)
    expect(inMonth[30]!.day).toBe(31)
  })

  it('flags active training days', () => {
    const weeks = buildMonthGrid(2026, 10, ['2026-10-05', '2026-10-06'])
    const cells = weeks.flat()
    expect(cells.filter((cell) => cell.active)).toHaveLength(2)
    expect(cells.find((cell) => cell.day === 5 && cell.inMonth)?.active).toBe(true)
    expect(cells.find((cell) => cell.day === 7 && cell.inMonth)?.active).toBe(false)
  })

  it('starts the month on the correct weekday', () => {
    const weeks = buildMonthGrid(2026, 10)
    const first = weeks[0]!
    const firstInMonth = first.findIndex((cell) => cell.inMonth)
    expect(firstInMonth).toBe(3) // Thursday
  })
})

describe('countActiveInGrid', () => {
  it('ignores padding days outside the month', () => {
    const weeks = buildMonthGrid(2026, 10, ['2026-10-05', '2026-09-28'])
    expect(countActiveInGrid(weeks)).toBe(1)
  })
})

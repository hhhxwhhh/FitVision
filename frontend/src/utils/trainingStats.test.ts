import { describe, expect, it } from 'vitest'
import {
  aggregate,
  periodSummaries,
  periodWindows,
  sessionMinutes,
  sessionsWithin,
  type SessionLike,
} from './trainingStats'

const session = (
  start: string,
  minutes: number,
  options: Partial<SessionLike> = {},
): SessionLike => {
  const startTime = new Date(start)
  const endTime = new Date(startTime.getTime() + minutes * 60000)
  return {
    start_time: startTime.toISOString(),
    end_time: endTime.toISOString(),
    is_completed: true,
    calories_burned: minutes * 6,
    performance_score: 80,
    ...options,
  }
}

describe('periodWindows', () => {
  it('starts the week window six days before the reference day', () => {
    const reference = new Date(2026, 9, 31, 15, 30)
    const { week } = periodWindows(reference)
    expect(week.start.getHours()).toBe(0)
    expect(week.end.getDate()).toBe(31)
    const calendarDays =
      (new Date(week.end.getFullYear(), week.end.getMonth(), week.end.getDate()).getTime() -
        new Date(week.start.getFullYear(), week.start.getMonth(), week.start.getDate()).getTime()) /
      86400000
    expect(calendarDays).toBe(6)
  })

  it('starts the month window on the first day of the month', () => {
    const { month } = periodWindows(new Date(2026, 9, 31))
    expect(month.start.getDate()).toBe(1)
    expect(month.start.getMonth()).toBe(9)
    expect(month.end.getDate()).toBe(31)
  })
})

describe('sessionMinutes', () => {
  it('returns the rounded duration', () => {
    expect(sessionMinutes(session('2026-10-31T10:00:00', 32))).toBe(32)
  })

  it('returns 0 while a session is still running', () => {
    expect(sessionMinutes({ ...session('2026-10-31T10:00:00', 10), end_time: null })).toBe(0)
  })
})

describe('sessionsWithin', () => {
  it('keeps only sessions inside the inclusive window', () => {
    const sessions = [
      session('2026-10-01T10:00:00', 30),
      session('2026-10-20T10:00:00', 30),
      session('2026-11-05T10:00:00', 30),
    ]
    const { month } = periodWindows(new Date(2026, 9, 31))
    const outside = sessions[2]
    const kept = sessionsWithin(sessions, month)
    expect(kept).toHaveLength(2)
    expect(kept).not.toContain(outside)
  })
})

describe('aggregate', () => {
  it('sums sessions and averages only scored sessions', () => {
    const stats = aggregate([
      session('2026-10-20T10:00:00', 30, { calories_burned: 200, performance_score: 90 }),
      session('2026-10-22T10:00:00', 30, { calories_burned: 100, performance_score: 0 }),
      session('2026-10-24T10:00:00', 30, { is_completed: false, performance_score: 70 }),
    ])

    expect(stats.count).toBe(3)
    expect(stats.completed).toBe(2)
    expect(stats.minutes).toBe(90)
    expect(stats.calories).toBe(480)
    expect(stats.avgScore).toBe(80)
  })

  it('returns zeroed counters for an empty list', () => {
    expect(aggregate([])).toEqual({
      count: 0,
      completed: 0,
      minutes: 0,
      calories: 0,
      avgScore: 0,
    })
  })
})

describe('periodSummaries', () => {
  it('splits counts between the trailing week and the calendar month', () => {
    const sessions = [
      session('2026-10-28T10:00:00', 30), // inside both windows
      session('2026-10-02T10:00:00', 30), // month only
      session('2026-09-28T10:00:00', 30), // neither
    ]
    const { week, month } = periodSummaries(sessions, new Date(2026, 9, 31))

    expect(week.count).toBe(1)
    expect(month.count).toBe(2)
  })
})

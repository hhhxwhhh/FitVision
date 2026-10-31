import { describe, expect, it } from 'vitest'
import {
  aggregate,
  currentStreak,
  dayKey,
  longestStreak,
  periodSummaries,
  periodWindows,
  sessionMinutes,
  sessionsWithin,
  trainingDays,
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

const daySession = (day: string): SessionLike => ({
  ...session(`${day}T09:00:00`, 30),
  start_time: new Date(`${day}T09:00:00`).toISOString(),
})

describe('dayKey', () => {
  it('formats a local calendar day', () => {
    expect(dayKey(new Date(2026, 0, 5, 22, 30))).toBe('2026-01-05')
    expect(dayKey('2026-03-09T10:00:00')).toBe('2026-03-09')
  })
})

describe('trainingDays', () => {
  it('collapses several sessions on the same day', () => {
    const days = trainingDays([
      daySession('2026-05-01'),
      daySession('2026-05-01'),
      daySession('2026-05-03'),
    ])
    expect(days).toEqual(['2026-05-01', '2026-05-03'])
  })
})

describe('longestStreak', () => {
  it('finds the longest run of consecutive days', () => {
    const sessions = ['2026-05-01', '2026-05-02', '2026-05-03', '2026-05-06'].map(daySession)
    expect(longestStreak(sessions)).toBe(3)
  })

  it('returns 1 for an isolated session and 0 with no data', () => {
    expect(longestStreak([daySession('2026-05-01')])).toBe(1)
    expect(longestStreak([])).toBe(0)
  })
})

describe('currentStreak', () => {
  it('counts back from today', () => {
    const today = new Date(2026, 4, 10)
    const sessions = ['2026-05-08', '2026-05-09', '2026-05-10'].map(daySession)
    expect(currentStreak(sessions, today)).toBe(3)
  })

  it('still counts when today has not been logged yet', () => {
    const today = new Date(2026, 4, 10)
    const sessions = ['2026-05-09', '2026-05-10'].map(daySession)
    expect(currentStreak(sessions, today)).toBe(2)
  })

  it('resets once a day is missed', () => {
    const today = new Date(2026, 4, 10)
    const sessions = ['2026-05-05', '2026-05-06'].map(daySession)
    expect(currentStreak(sessions, today)).toBe(0)
  })
})

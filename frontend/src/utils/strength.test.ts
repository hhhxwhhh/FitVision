import { describe, expect, it } from 'vitest'

import {
  exercisesWithData,
  formatE1rm,
  parseStrength,
  parseStrengthExercise,
  parseStrengthPoint,
  parseStrengthSummary,
  prescriptionText,
  trendText,
  trendType,
} from './strength'

const point = { date: '2026-10-20', e1rm: 92.5, weight: 80, reps: 5, method: 'rep_formula' }

const summary = {
  latest: 92.5,
  best: 95,
  trend: 1.2,
  trend_percent: 6.5,
  sessions: 4,
  first_session: '2026-10-01',
  deload: { deload: false, factor: 1, reasons: [], advice: '' },
}

const exercise = {
  exercise_id: 7,
  name: '杠铃卧推',
  target_muscle: 'chest',
  e1rm: 92.5,
  best: 95,
  trend: 1.2,
  points: [point],
  summary,
}

describe('parseStrengthPoint', () => {
  it('keeps a well-formed point', () => {
    expect(parseStrengthPoint(point)?.e1rm).toBe(92.5)
  })

  it('rejects points without a usable e1rm', () => {
    expect(parseStrengthPoint({ date: '2026-10-20' })).toBeNull()
    expect(parseStrengthPoint({ e1rm: 0 })).toBeNull()
    expect(parseStrengthPoint(null)).toBeNull()
  })

  it('fills in defaults', () => {
    const parsed = parseStrengthPoint({ e1rm: 50 })
    expect(parsed?.weight).toBe(0)
    expect(parsed?.reps).toBe(0)
    expect(parsed?.method).toBe('rep_formula')
  })
})

describe('parseStrengthSummary', () => {
  it('reads a full summary', () => {
    const parsed = parseStrengthSummary(summary)
    expect(parsed.latest).toBe(92.5)
    expect(parsed.sessions).toBe(4)
    expect(parsed.deload.deload).toBe(false)
  })

  it('degrades to zeros', () => {
    const parsed = parseStrengthSummary(undefined)
    expect(parsed.latest).toBe(0)
    expect(parsed.deload.reasons).toEqual([])
    expect(parsed.deload.factor).toBe(1)
  })

  it('keeps only string reasons', () => {
    const parsed = parseStrengthSummary({ deload: { deload: true, reasons: ['a', 3] } })
    expect(parsed.deload.reasons).toEqual(['a'])
  })
})

describe('parseStrengthExercise', () => {
  it('reads a full exercise', () => {
    const parsed = parseStrengthExercise(exercise)
    expect(parsed?.exercise_id).toBe(7)
    expect(parsed?.points).toHaveLength(1)
    expect(parsed?.summary.best).toBe(95)
  })

  it('rejects entries without an id', () => {
    expect(parseStrengthExercise({ name: 'x' })).toBeNull()
    expect(parseStrengthExercise(null)).toBeNull()
  })

  it('drops broken points but keeps the exercise', () => {
    const parsed = parseStrengthExercise({ ...exercise, points: [point, { e1rm: 0 }, null] })
    expect(parsed?.points).toHaveLength(1)
  })

  it('falls back to a generated name', () => {
    expect(parseStrengthExercise({ exercise_id: 3 })?.name).toBe('动作 #3')
  })
})

describe('parseStrength', () => {
  it('round-trips a payload', () => {
    const parsed = parseStrength({ days: 120, exercises: [exercise], prescription: null })
    expect(parsed?.exercises).toHaveLength(1)
    expect(parsed?.days).toBe(120)
    expect(parsed?.prescription).toBeNull()
  })

  it('reads the prescription', () => {
    const parsed = parseStrength({
      days: 120,
      exercises: [exercise],
      prescription: {
        available: true,
        weight: 82.5,
        target_reps: 6,
        target_rir: 2,
        changed: true,
        reason: 'ok',
      },
    })
    expect(parsed?.prescription?.available).toBe(true)
    expect(parsed?.prescription?.weight).toBe(82.5)
  })

  it('marks an unavailable prescription', () => {
    const parsed = parseStrength({
      days: 120,
      exercises: [],
      prescription: { available: false, reason: '还没有数据' },
    })
    expect(parsed?.prescription?.available).toBe(false)
    expect(parsed?.prescription?.reason).toBe('还没有数据')
  })

  it('returns null for a malformed payload', () => {
    expect(parseStrength(null)).toBeNull()
    expect(parseStrength({})).toBeNull()
    expect(parseStrength({ exercises: 'nope' })).toBeNull()
  })
})

describe('trend helpers', () => {
  it('describes the direction', () => {
    expect(trendText(1.2)).toBe('上升')
    expect(trendText(-0.8)).toBe('回落')
    expect(trendText(0.05)).toBe('持平')
    expect(trendText(null)).toBe('持平')
  })

  it('maps the direction to a tag type', () => {
    expect(trendType(1)).toBe('up')
    expect(trendType(-1)).toBe('down')
    expect(trendType(0)).toBe('flat')
  })
})

describe('formatE1rm', () => {
  it('drops the decimals for whole numbers', () => {
    expect(formatE1rm(100)).toBe('100')
    expect(formatE1rm(92.5)).toBe('92.5')
  })

  it('handles missing values', () => {
    expect(formatE1rm(null)).toBe('—')
    expect(formatE1rm(0)).toBe('—')
  })
})

describe('prescriptionText', () => {
  it('describes an available prescription', () => {
    const text = prescriptionText({
      available: true,
      weight: 82.5,
      target_reps: 6,
      target_rir: 2,
    })
    expect(text).toContain('82.5 kg')
    expect(text).toContain('6 次')
  })

  it('explains why there is none', () => {
    expect(prescriptionText(null)).toContain('还没有足够')
    expect(prescriptionText({ available: false, reason: '没有负重记录' })).toBe('没有负重记录')
  })
})

describe('exercisesWithData', () => {
  it('keeps only exercises with points, best first', () => {
    const empty = { ...exercise, exercise_id: 1, best: 200, points: [] }
    const parsed = exercisesWithData([empty, exercise])
    expect(parsed).toHaveLength(1)
    expect(parsed[0]?.exercise_id).toBe(7)
  })
})

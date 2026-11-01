import { describe, expect, it } from 'vitest'

import {
  MUSCLE_STATUS_LABEL,
  concentrationLabel,
  formatVolume,
  muscleStatusLabel,
  parseVolume,
  parseVolumeMuscle,
  parseVolumeSession,
  parseVolumeWeek,
  trendLabel,
  trendTone,
} from './volume'

describe('trendTone', () => {
  it('maps known trends', () => {
    expect(trendTone('rising')).toBe('up')
    expect(trendTone('falling')).toBe('down')
    expect(trendTone('steady')).toBe('flat')
    expect(trendTone('unknown')).toBe('none')
  })

  it('falls back for unknown keys', () => {
    expect(trendTone('nonsense')).toBe('none')
    expect(trendTone(null)).toBe('none')
    expect(trendTone(undefined)).toBe('none')
  })
})

describe('trendLabel', () => {
  it('returns a Chinese label', () => {
    expect(trendLabel('rising')).toBe('稳步上升')
    expect(trendLabel('falling')).toBe('有所下滑')
    expect(trendLabel('steady')).toBe('基本持平')
  })

  it('prefers an explicit fallback', () => {
    expect(trendLabel('rising', '自定义')).toBe('自定义')
  })

  it('handles unknown keys', () => {
    expect(trendLabel('mystery')).toBe('mystery')
    expect(trendLabel(null)).toBe('—')
  })
})

describe('muscleStatusLabel', () => {
  it('maps known statuses', () => {
    expect(muscleStatusLabel('low')).toBe('偏低')
    expect(muscleStatusLabel('ok')).toBe('正常')
    expect(muscleStatusLabel('high')).toBe('偏高')
  })

  it('falls back for unknown statuses', () => {
    expect(muscleStatusLabel('weird')).toBe('未知')
    expect(muscleStatusLabel(undefined)).toBe('未知')
  })

  it('exports the raw label map', () => {
    expect(MUSCLE_STATUS_LABEL.ok).toBe('正常')
  })
})

describe('parseVolumeMuscle', () => {
  it('parses a full payload', () => {
    const result = parseVolumeMuscle({
      muscle: 'chest',
      label: '胸部',
      sets: 12,
      weeks: 4,
      tonnage: 24000,
      intensity_volume: 16800,
      effective_volume: 16800,
      share: 0.42,
      status: 'ok',
    })
    expect(result?.muscle).toBe('chest')
    expect(result?.label).toBe('胸部')
    expect(result?.sets).toBe(12)
    expect(result?.share).toBeCloseTo(0.42)
    expect(result?.status).toBe('ok')
  })

  it('rejects entries without a muscle key', () => {
    expect(parseVolumeMuscle({ label: '胸部' })).toBeNull()
    expect(parseVolumeMuscle(null)).toBeNull()
    expect(parseVolumeMuscle('nope')).toBeNull()
  })

  it('defaults numbers and status', () => {
    const result = parseVolumeMuscle({ muscle: 'chest' })
    expect(result?.sets).toBe(0)
    expect(result?.effective_volume).toBe(0)
    expect(result?.status).toBe('unknown')
    expect(result?.label).toBe('chest')
  })

  it('coerces string numbers', () => {
    const result = parseVolumeMuscle({ muscle: 'chest', effective_volume: '1234.5' })
    expect(result?.effective_volume).toBeCloseTo(1234.5)
  })

  it('rejects invalid status values', () => {
    const result = parseVolumeMuscle({ muscle: 'chest', status: 'bogus' })
    expect(result?.status).toBe('unknown')
  })
})

describe('parseVolumeSession', () => {
  it('parses a session', () => {
    const result = parseVolumeSession({
      date: '2026-03-01',
      sets: 10,
      measurable_sets: 9,
      tonnage: 4000,
      intensity_volume: 2800,
      effective_volume: 2750,
    })
    expect(result?.date).toBe('2026-03-01')
    expect(result?.sets).toBe(10)
    expect(result?.measurable_sets).toBe(9)
  })

  it('rejects non-objects', () => {
    expect(parseVolumeSession(null)).toBeNull()
    expect(parseVolumeSession(42)).toBeNull()
  })
})

describe('parseVolumeWeek', () => {
  it('parses a week', () => {
    const result = parseVolumeWeek({ year: 2026, week: 10, sessions: 3, sets: 24 })
    expect(result?.year).toBe(2026)
    expect(result?.week).toBe(10)
    expect(result?.sessions).toBe(3)
  })

  it('rejects non-objects', () => {
    expect(parseVolumeWeek(undefined)).toBeNull()
  })
})

describe('parseVolume', () => {
  const base = {
    available: true,
    days: 56,
    weeks: 8,
    total_tonnage: 10000,
    total_intensity_volume: 7000,
    total_effective_volume: 6900,
    concentration: 0.4,
    trend: 'rising',
    trend_slope: 0.03,
    verdict: '容量稳步上升',
    advice: ['保持节奏'],
  }

  it('parses a full payload', () => {
    const result = parseVolume({
      ...base,
      sessions: [{ date: '2026-03-01', sets: 10 }],
      weekly: [{ year: 2026, week: 10 }],
      muscles: [{ muscle: 'chest', label: '胸部' }],
    })
    expect(result?.available).toBe(true)
    expect(result?.sessions).toHaveLength(1)
    expect(result?.weekly).toHaveLength(1)
    expect(result?.muscles).toHaveLength(1)
    expect(result?.trend).toBe('rising')
    expect(result?.advice).toEqual(['保持节奏'])
  })

  it('handles an empty payload', () => {
    const result = parseVolume({})
    expect(result?.available).toBe(false)
    expect(result?.sessions).toEqual([])
    expect(result?.muscles).toEqual([])
    expect(result?.trend).toBe('unknown')
    expect(result?.verdict).toBe('数据不足')
  })

  it('rejects non-objects', () => {
    expect(parseVolume(null)).toBeNull()
    expect(parseVolume('nope')).toBeNull()
  })

  it('drops malformed nested entries', () => {
    const result = parseVolume({
      sessions: [null, { date: '2026-03-01' }],
      weekly: ['bad'],
      muscles: [{ label: 'no muscle key' }],
    })
    expect(result?.sessions).toHaveLength(1)
    expect(result?.weekly).toHaveLength(0)
    expect(result?.muscles).toHaveLength(0)
  })

  it('rejects invalid trend values', () => {
    const result = parseVolume({ ...base, trend: 'sideways' })
    expect(result?.trend).toBe('unknown')
  })
})

describe('concentrationLabel', () => {
  it('describes high concentration', () => {
    expect(concentrationLabel(0.9)).toBe('容量几乎全在一个部位')
    expect(concentrationLabel(0.6)).toBe('容量分布明显不均')
  })

  it('describes balanced distribution', () => {
    expect(concentrationLabel(0.1)).toBe('容量分布均衡')
  })

  it('handles degenerate input', () => {
    expect(concentrationLabel(0)).toBe('容量分布很集中')
    expect(concentrationLabel(Number.NaN)).toBe('容量分布很集中')
  })
})

describe('formatVolume', () => {
  it('formats small values with separators', () => {
    expect(formatVolume(3200)).toBe('3,200')
  })

  it('formats large values in ten-thousands', () => {
    expect(formatVolume(25000)).toBe('2.5 万')
  })

  it('handles zero and invalid input', () => {
    expect(formatVolume(0)).toBe('0')
    expect(formatVolume(-5)).toBe('0')
    expect(formatVolume(Number.NaN)).toBe('0')
  })
})

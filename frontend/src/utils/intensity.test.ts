import { describe, expect, it } from 'vitest'
import {
  ZONE_LABEL,
  balanceLabel,
  parseIntensity,
  parseIntensitySession,
  parseIntensityWeek,
  parseIntensityZone,
  zoneLabel,
  zoneShareText,
  zoneTone,
} from './intensity'

describe('zoneTone', () => {
  it('maps every known zone to a tone', () => {
    expect(zoneTone('zone_1')).toBe('calm')
    expect(zoneTone('zone_2')).toBe('steady')
    expect(zoneTone('zone_3')).toBe('warm')
    expect(zoneTone('zone_4')).toBe('hot')
  })

  it('falls back to calm for unknown keys', () => {
    expect(zoneTone('zone_9')).toBe('calm')
    expect(zoneTone(null)).toBe('calm')
  })
})

describe('zoneLabel', () => {
  it('uses the built-in Chinese names', () => {
    expect(zoneLabel('zone_1')).toBe('恢复')
    expect(zoneLabel('zone_4')).toBe('强度')
  })

  it('prefers the fallback provided by the server', () => {
    expect(zoneLabel('zone_4', '峰值')).toBe('峰值')
  })

  it('returns a dash for missing keys', () => {
    expect(zoneLabel('')).toBe('—')
    expect(zoneLabel(null)).toBe('—')
  })

  it('exposes the label map', () => {
    expect(ZONE_LABEL.zone_2).toBe('基础')
  })
})

describe('parseIntensityZone', () => {
  it('parses a full zone', () => {
    const zone = parseIntensityZone({
      key: 'zone_4',
      label: '强度',
      sets: 6,
      share: 0.25,
      target_share: 0.15,
      deviation: 0.1,
      load: 480,
    })
    expect(zone?.sets).toBe(6)
    expect(zone?.deviation).toBeCloseTo(0.1)
  })

  it('rejects a zone without a key', () => {
    expect(parseIntensityZone({ sets: 3 })).toBeNull()
    expect(parseIntensityZone(null)).toBeNull()
    expect(parseIntensityZone('nope')).toBeNull()
  })

  it('defaults the numeric fields to zero', () => {
    const zone = parseIntensityZone({ key: 'zone_1' })
    expect(zone?.sets).toBe(0)
    expect(zone?.share).toBe(0)
  })
})

describe('parseIntensitySession', () => {
  it('parses a session with zones', () => {
    const session = parseIntensitySession({
      date: '2026-03-01',
      sets: 10,
      zones: [{ key: 'zone_2', sets: 6 }, { key: 'zone_4', sets: 4 }],
      rpe_trimp: 720,
      intensity_trimp: 810,
      high_intensity_sets: 4,
      balanced: false,
      notes: ['强度分布偏向高强度区间：强度（40%）。'],
    })
    expect(session?.zones).toHaveLength(2)
    expect(session?.high_intensity_sets).toBe(4)
    expect(session?.balanced).toBe(false)
    expect(session?.notes[0]).toContain('偏向')
  })

  it('derives the set count from the zones when missing', () => {
    const session = parseIntensitySession({
      date: '2026-03-01',
      zones: [{ key: 'zone_1', sets: 3 }, { key: 'zone_3', sets: 5 }],
    })
    expect(session?.sets).toBe(8)
  })

  it('rejects a non-object', () => {
    expect(parseIntensitySession(undefined)).toBeNull()
  })
})

describe('parseIntensityWeek', () => {
  it('parses a week bucket', () => {
    const week = parseIntensityWeek({
      year: 2026,
      week: 9,
      sessions: 3,
      sets: 40,
      zones: [{ key: 'zone_3', sets: 20, share: 0.5 }],
      rpe_trimp: 3000,
      high_intensity_sets: 6,
      high_intensity_days: 1,
      over_high_intensity_cap: false,
    })
    expect(week?.week).toBe(9)
    expect(week?.zones[0]?.share).toBeCloseTo(0.5)
    expect(week?.over_high_intensity_cap).toBe(false)
  })

  it('rejects a non-object', () => {
    expect(parseIntensityWeek(42)).toBeNull()
  })
})

describe('parseIntensity', () => {
  const payload = {
    available: true,
    days: 28,
    weeks: 4,
    sessions: [{ date: '2026-03-01', sets: 8, zones: [{ key: 'zone_2', sets: 8 }] }],
    weekly: [{ year: 2026, week: 9, sessions: 1, sets: 8, zones: [] }],
    balance_score: 0.82,
    verdict: '基本合理',
    advice: ['高强度占比偏高。'],
  }

  it('parses the whole payload', () => {
    const result = parseIntensity(payload)
    expect(result?.available).toBe(true)
    expect(result?.balance_score).toBeCloseTo(0.82)
    expect(result?.verdict).toBe('基本合理')
    expect(result?.advice).toHaveLength(1)
  })

  it('rejects a non-object', () => {
    expect(parseIntensity(null)).toBeNull()
    expect(parseIntensity('x')).toBeNull()
  })

  it('handles the unavailable shape', () => {
    const result = parseIntensity({
      available: false,
      reason: '还没有带重量或 RPE 的训练记录',
      sessions: [],
      weekly: [],
      balance_score: 0,
      verdict: '数据不足',
      advice: [],
    })
    expect(result?.available).toBe(false)
    expect(result?.reason).toContain('RPE')
    expect(result?.verdict).toBe('数据不足')
  })

  it('tolerates missing collections', () => {
    const result = parseIntensity({ available: true })
    expect(result?.sessions).toEqual([])
    expect(result?.weekly).toEqual([])
    expect(result?.balance_score).toBe(0)
  })
})

describe('balanceLabel', () => {
  it('describes every score band', () => {
    expect(balanceLabel(0.95)).toContain('均衡')
    expect(balanceLabel(0.8)).toContain('合理')
    expect(balanceLabel(0.65)).toContain('轻度')
    expect(balanceLabel(0.3)).toContain('明显')
  })

  it('handles the missing-data case', () => {
    expect(balanceLabel(0)).toContain('数据')
    expect(balanceLabel(Number.NaN)).toContain('数据')
  })
})

describe('zoneShareText', () => {
  it('formats the label and the percentage', () => {
    const zone = parseIntensityZone({ key: 'zone_4', sets: 5, share: 0.25 })
    expect(zoneShareText(zone!)).toBe('强度 25%')
  })
})

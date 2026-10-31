import { describe, expect, it } from 'vitest'
import {
  ACWR_DANGER,
  acwrPercent,
  acwrText,
  acwrTone,
  formatNumber,
  intensityText,
  parseLoadModel,
  restText,
  trendText,
  tsbText,
  volumeText,
  weeklyBars,
} from './loadModel'

const basePayload = {
  score: 72,
  tone: 'good',
  label: '适合训练',
  advice: '状态稳定',
  intensity: 'moderate',
  volume_multiplier: 0.9,
  acwr: 1.05,
  fitness: 420.5,
  fatigue: 380.2,
  tsb: 40.3,
  monotony: 1.2,
  strain: 620,
  form_trend: 1.4,
  rest_days: 2,
  weekly_load: 240,
  weekly_loads: [180, 210, 260, 240],
  acute_load: 34.2,
  chronic_load: 32.6,
  reasons: ['体能储备高于疲劳', '动作质量持续上升'],
}

describe('parseLoadModel', () => {
  it('returns null for missing or primitive payloads', () => {
    expect(parseLoadModel(undefined)).toBeNull()
    expect(parseLoadModel(null)).toBeNull()
    expect(parseLoadModel('nope')).toBeNull()
  })

  it('returns null when the payload predates the load model', () => {
    expect(parseLoadModel({ score: 70, tone: 'good' })).toBeNull()
    expect(parseLoadModel({ acwr: 'not-a-number' })).toBeNull()
  })

  it('narrows a full payload and defaults the missing numbers', () => {
    const model = parseLoadModel(basePayload)
    expect(model).not.toBeNull()
    expect(model?.acwr).toBe(1.05)
    expect(model?.weekly_loads).toEqual([180, 210, 260, 240])
    expect(model?.reasons).toHaveLength(2)
  })

  it('discards junk entries inside the list fields', () => {
    const model = parseLoadModel({
      ...basePayload,
      weekly_loads: [10, 'x', 20, null],
      reasons: ['ok', 42, null],
    })
    expect(model?.weekly_loads).toEqual([10, 20])
    expect(model?.reasons).toEqual(['ok'])
  })
})

describe('formatting helpers', () => {
  it('formats numbers with fixed digits', () => {
    expect(formatNumber(1.2345, 2)).toBe('1.23')
    expect(formatNumber(40)).toBe('40.0')
    expect(formatNumber(Number.NaN)).toBe('—')
  })

  it('reads the workload ratio', () => {
    expect(acwrText(parseLoadModel(basePayload))).toBe('1.05')
    expect(acwrText(null)).toBe('—')
  })

  it('classifies the workload ratio against the sweet spot', () => {
    const withRatio = (acwr: number) => parseLoadModel({ ...basePayload, acwr })
    expect(acwrTone(withRatio(1.0))).toBe('ok')
    expect(acwrTone(withRatio(1.31))).toBe('watch')
    expect(acwrTone(withRatio(0.7))).toBe('watch')
    expect(acwrTone(withRatio(ACWR_DANGER))).toBe('risk')
    expect(acwrTone(null)).toBe('ok')
  })

  it('maps the ratio onto a 0-100 bar position and clamps it', () => {
    const withRatio = (acwr: number) => parseLoadModel({ ...basePayload, acwr })
    // 0.5 -> 0%, 1.25 -> 50%, 2.0 -> 100%
    expect(acwrPercent(withRatio(0.5))).toBe(0)
    expect(acwrPercent(withRatio(1.25))).toBe(50)
    expect(acwrPercent(withRatio(2))).toBe(100)
    expect(acwrPercent(withRatio(5))).toBe(100)
    expect(acwrPercent(withRatio(0))).toBe(0)
    expect(acwrPercent(null)).toBe(0)
  })

  it('explains TSB in words', () => {
    const withTsb = (tsb: number) => parseLoadModel({ ...basePayload, tsb })
    expect(tsbText(withTsb(40.3))).toBe('体能 +40')
    expect(tsbText(withTsb(-12.6))).toBe('疲劳 -13')
    expect(tsbText(withTsb(0))).toBe('平衡')
    expect(tsbText(null)).toBe('—')
  })

  it('explains the rest gap', () => {
    const withDays = (rest_days: number) => parseLoadModel({ ...basePayload, rest_days })
    expect(restText(withDays(0))).toBe('今天已练')
    expect(restText(withDays(2))).toBe('2 天前')
    expect(restText(withDays(-1))).toBe('暂无记录')
    expect(restText(null)).toBe('—')
  })

  it('maps the suggested intensity to Chinese labels', () => {
    const withIntensity = (intensity: string) => parseLoadModel({ ...basePayload, intensity })
    expect(intensityText(withIntensity('rest'))).toBe('主动恢复')
    expect(intensityText(withIntensity('hard'))).toBe('高强度')
    expect(intensityText(withIntensity('unknown'))).toBe('按计划')
  })

  it('reads the form trend', () => {
    const withTrend = (form_trend: number) => parseLoadModel({ ...basePayload, form_trend })
    expect(trendText(withTrend(1.4))).toBe('+1.4 / 次')
    expect(trendText(withTrend(-2.2))).toBe('-2.2 / 次')
    expect(trendText(withTrend(0.1))).toBe('持平')
  })

  it('reads the suggested volume', () => {
    expect(volumeText(parseLoadModel(basePayload))).toBe('90%')
    expect(volumeText(null)).toBe('—')
  })
})

describe('weeklyBars', () => {
  it('normalises against the peak week', () => {
    expect(weeklyBars([100, 200, 50])).toEqual([50, 100, 25])
  })

  it('handles empty and all-zero series', () => {
    expect(weeklyBars([])).toEqual([])
    expect(weeklyBars([0, 0, 0])).toEqual([0, 0, 0])
  })

  it('ignores negative values', () => {
    expect(weeklyBars([-10, 20])).toEqual([0, 100])
  })
})

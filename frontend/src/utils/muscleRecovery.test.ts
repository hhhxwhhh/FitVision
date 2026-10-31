import { describe, expect, it } from 'vitest'

import {
  FATIGUED_THRESHOLD,
  READY_THRESHOLD,
  hoursToReadyText,
  labelsFor,
  multiplierHint,
  parseMuscleRecovery,
  parseMuscleState,
  recoveryStatus,
  sortByFatigue,
  statusLabel,
  volumeHint,
  type MuscleRecoveryState,
} from './muscleRecovery'

function state(overrides: Partial<MuscleRecoveryState> = {}): MuscleRecoveryState {
  return {
    muscle: 'chest',
    label: '胸部',
    residual: 0,
    recovery: 100,
    status: 'ready',
    hours_to_ready: 0,
    weekly_sets: 0,
    volume_status: 'idle',
    multiplier: 1.15,
    ...overrides,
  }
}

describe('recoveryStatus', () => {
  it('mirrors the backend thresholds', () => {
    expect(recoveryStatus(READY_THRESHOLD)).toBe('ready')
    expect(recoveryStatus(READY_THRESHOLD - 0.1)).toBe('caution')
    expect(recoveryStatus(FATIGUED_THRESHOLD)).toBe('caution')
    expect(recoveryStatus(FATIGUED_THRESHOLD - 0.1)).toBe('fatigued')
  })

  it('falls back to ready for junk input', () => {
    expect(recoveryStatus(null)).toBe('ready')
    expect(recoveryStatus(Number.NaN)).toBe('ready')
  })

  it('accepts numeric strings', () => {
    expect(recoveryStatus('40' as unknown as number)).toBe('fatigued')
  })
})

describe('statusLabel / volumeHint', () => {
  it('labels every status', () => {
    expect(statusLabel('ready')).toBe('已恢复')
    expect(statusLabel('caution')).toBe('恢复中')
    expect(statusLabel('fatigued')).toBe('酸痛中')
  })

  it('hints every volume band', () => {
    expect(volumeHint('under')).toContain('偏低')
    expect(volumeHint('optimal')).toContain('合适')
    expect(volumeHint('over')).toContain('偏多')
    expect(volumeHint('idle')).toContain('还没练')
  })
})

describe('hoursToReadyText', () => {
  it('reports full recovery at zero', () => {
    expect(hoursToReadyText(0)).toBe('已恢复')
    expect(hoursToReadyText(-5)).toBe('已恢复')
  })

  it('uses hours below a day', () => {
    expect(hoursToReadyText(6.4)).toBe('约 6 小时')
  })

  it('switches to days above 24 hours', () => {
    expect(hoursToReadyText(50)).toBe('约 2 天')
  })

  it('degrades gracefully', () => {
    expect(hoursToReadyText(null)).toBe('已恢复')
  })
})

describe('multiplierHint', () => {
  it('explains the whole range', () => {
    expect(multiplierHint(1.15)).toContain('加量')
    expect(multiplierHint(1.0)).toContain('正常')
    expect(multiplierHint(0.85)).toContain('降低')
    expect(multiplierHint(0.55)).toContain('避开')
  })
})

describe('parseMuscleState', () => {
  it('keeps a well-formed payload', () => {
    const parsed = parseMuscleState({ muscle: 'legs', label: '腿部', recovery: 42.5 })
    expect(parsed?.muscle).toBe('legs')
    expect(parsed?.recovery).toBe(42.5)
    expect(parsed?.status).toBe('fatigued')
  })

  it('derives the status when the backend omits it', () => {
    expect(parseMuscleState({ muscle: 'abs', recovery: 90 })?.status).toBe('ready')
  })

  it('falls back to the muscle key as the label', () => {
    expect(parseMuscleState({ muscle: 'back' })?.label).toBe('back')
  })

  it('clamps the recovery percentage', () => {
    expect(parseMuscleState({ muscle: 'arms', recovery: 180 })?.recovery).toBe(100)
    expect(parseMuscleState({ muscle: 'arms', recovery: -20 })?.recovery).toBe(0)
  })

  it('rejects malformed rows', () => {
    expect(parseMuscleState(null)).toBeNull()
    expect(parseMuscleState('legs')).toBeNull()
    expect(parseMuscleState({ label: '腿部' })).toBeNull()
    expect(parseMuscleState({ muscle: '' })).toBeNull()
  })

  it('tolerates garbage numbers', () => {
    const parsed = parseMuscleState({ muscle: 'chest', recovery: 'oops', weekly_sets: null })
    expect(parsed?.recovery).toBe(100)
    expect(parsed?.weekly_sets).toBe(0)
    expect(parsed?.volume_status).toBe('idle')
  })
})

describe('parseMuscleRecovery', () => {
  const payload = {
    muscles: [
      { muscle: 'legs', label: '腿部', recovery: 35, status: 'fatigued' },
      { muscle: 'chest', label: '胸部', recovery: 100, status: 'ready' },
    ],
    focus: ['chest'],
    avoid: ['legs'],
  }

  it('round-trips a valid payload', () => {
    const parsed = parseMuscleRecovery(payload)
    expect(parsed?.muscles).toHaveLength(2)
    expect(parsed?.focus).toEqual(['chest'])
    expect(parsed?.avoid).toEqual(['legs'])
  })

  it('drops unusable rows but keeps the rest', () => {
    const parsed = parseMuscleRecovery({ ...payload, muscles: [...payload.muscles, { label: 'x' }, null] })
    expect(parsed?.muscles).toHaveLength(2)
  })

  it('returns null when there is nothing to show', () => {
    expect(parseMuscleRecovery(null)).toBeNull()
    expect(parseMuscleRecovery({})).toBeNull()
    expect(parseMuscleRecovery({ muscles: [] })).toBeNull()
    expect(parseMuscleRecovery({ muscles: [null] })).toBeNull()
  })

  it('ignores non-string focus entries', () => {
    const parsed = parseMuscleRecovery({ muscles: payload.muscles, focus: ['chest', 7, null] })
    expect(parsed?.focus).toEqual(['chest'])
  })

  it('defaults focus and avoid to empty arrays', () => {
    const parsed = parseMuscleRecovery({ muscles: payload.muscles })
    expect(parsed?.focus).toEqual([])
    expect(parsed?.avoid).toEqual([])
  })
})

describe('sortByFatigue', () => {
  it('puts the sorest muscle first', () => {
    const sorted = sortByFatigue([state({ recovery: 100 }), state({ muscle: 'legs', recovery: 20 })])
    expect(sorted[0]?.muscle).toBe('legs')
  })

  it('does not mutate the input', () => {
    const input = [state({ recovery: 100 }), state({ muscle: 'legs', recovery: 20 })]
    sortByFatigue(input)
    expect(input[0]?.muscle).toBe('chest')
  })
})

describe('labelsFor', () => {
  it('maps muscle keys to Chinese labels', () => {
    const states = [state({ muscle: 'chest', label: '胸部' }), state({ muscle: 'legs', label: '腿部' })]
    expect(labelsFor(states, ['legs', 'chest'])).toEqual(['腿部', '胸部'])
  })

  it('falls back to the key for unknown muscles', () => {
    expect(labelsFor([], ['neck'])).toEqual(['neck'])
  })
})

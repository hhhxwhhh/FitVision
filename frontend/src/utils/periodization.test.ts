import { describe, expect, it } from 'vitest'

import {
  autoregulationText,
  deloadWeek,
  exerciseText,
  heaviestWeek,
  intensityHint,
  parseMesocycle,
  parseMesocycleExercise,
  parseMesocycleSession,
  parseMesocycleSlot,
  parseMesocycleWeek,
  phaseLabel,
  phaseTone,
  slotText,
  volumeHint,
} from './periodization'

function exercise(overrides: Record<string, unknown> = {}) {
  return {
    exercise_id: 7,
    name: '杠铃卧推',
    sets: 3,
    reps: 8,
    weight: 62.5,
    e1rm: 90,
    based_on_e1rm: true,
    equipment: 'barbell',
    note: '按 e1RM 折算',
    ...overrides,
  }
}

function slot(overrides: Record<string, unknown> = {}) {
  return {
    muscle: 'chest',
    label: '胸部',
    sets: 4,
    reps: 8,
    weight: 62.5,
    e1rm: 90,
    based_on_e1rm: true,
    note: '按 e1RM 折算',
    exercises: [exercise()],
    ...overrides,
  }
}

function session(overrides: Record<string, unknown> = {}) {
  return {
    index: 1,
    label: '第 1 天',
    focus: ['chest'],
    slots: [slot()],
    total_sets: 4,
    ...overrides,
  }
}

function week(overrides: Record<string, unknown> = {}) {
  return {
    index: 1,
    phase: 'accumulation',
    label: '积累',
    note: '容量最高',
    volume: 1,
    intensity: 0.72,
    reps_low: 8,
    reps_high: 12,
    rir: 3,
    total_sets: 16,
    sessions: [session()],
    ...overrides,
  }
}

function payload(overrides: Record<string, unknown> = {}) {
  return {
    weeks: [week(), week({ index: 2, phase: 'deload', label: '减量', total_sets: 8 })],
    days_per_week: 4,
    readiness: 88,
    focus: ['chest'],
    avoid: ['legs'],
    autoregulation: 1,
    notes: ['当前准备度 88 分'],
    total_weeks: 2,
    total_sets: 24,
    ...overrides,
  }
}

describe('parseMesocycleExercise', () => {
  it('parses an exercise', () => {
    const parsed = parseMesocycleExercise(exercise())
    expect(parsed?.exercise_id).toBe(7)
    expect(parsed?.name).toBe('杠铃卧推')
    expect(parsed?.sets).toBe(3)
  })

  it('rejects entries without an id', () => {
    expect(parseMesocycleExercise({ name: '卧推' })).toBeNull()
  })

  it('falls back to a generic name', () => {
    const parsed = parseMesocycleExercise({ exercise_id: 3 })
    expect(parsed?.name).toBe('动作 #3')
  })
})

describe('parseMesocycleSlot', () => {
  it('parses a full slot', () => {
    const parsed = parseMesocycleSlot(slot())
    expect(parsed?.muscle).toBe('chest')
    expect(parsed?.sets).toBe(4)
    expect(parsed?.weight).toBe(62.5)
    expect(parsed?.based_on_e1rm).toBe(true)
  })

  it('parses the nested exercises', () => {
    const parsed = parseMesocycleSlot(slot())
    expect(parsed?.exercises).toHaveLength(1)
    expect(parsed?.exercises[0]?.name).toBe('杠铃卧推')
  })

  it('defaults to an empty exercise list', () => {
    const parsed = parseMesocycleSlot({ muscle: 'chest' })
    expect(parsed?.exercises).toEqual([])
  })

  it('drops malformed exercises', () => {
    const parsed = parseMesocycleSlot(slot({ exercises: [exercise(), { name: 'x' }] }))
    expect(parsed?.exercises).toHaveLength(1)
  })

  it('rejects payloads without a muscle', () => {
    expect(parseMesocycleSlot({ label: '胸部' })).toBeNull()
  })

  it('rejects non-objects', () => {
    expect(parseMesocycleSlot(null)).toBeNull()
    expect(parseMesocycleSlot('chest')).toBeNull()
  })

  it('falls back to the muscle key when the label is missing', () => {
    const parsed = parseMesocycleSlot({ muscle: 'legs' })
    expect(parsed?.label).toBe('legs')
  })
})

describe('parseMesocycleSession', () => {
  it('parses sessions and their slots', () => {
    const parsed = parseMesocycleSession(session())
    expect(parsed?.slots).toHaveLength(1)
    expect(parsed?.focus).toEqual(['chest'])
  })

  it('derives the total sets when the field is missing', () => {
    const parsed = parseMesocycleSession(session({ total_sets: undefined }))
    expect(parsed?.total_sets).toBe(4)
  })

  it('drops malformed slots', () => {
    const parsed = parseMesocycleSession(session({ slots: [slot(), { label: 'x' }] }))
    expect(parsed?.slots).toHaveLength(1)
  })
})

describe('parseMesocycleWeek', () => {
  it('parses a week', () => {
    const parsed = parseMesocycleWeek(week())
    expect(parsed?.phase).toBe('accumulation')
    expect(parsed?.sessions).toHaveLength(1)
  })

  it('derives the total sets when the field is missing', () => {
    const parsed = parseMesocycleWeek(week({ total_sets: undefined }))
    expect(parsed?.total_sets).toBe(4)
  })
})

describe('parseMesocycle', () => {
  it('parses the whole payload', () => {
    const parsed = parseMesocycle(payload())
    expect(parsed?.weeks).toHaveLength(2)
    expect(parsed?.total_weeks).toBe(2)
    expect(parsed?.days_per_week).toBe(4)
  })

  it('rejects payloads without weeks', () => {
    expect(parseMesocycle({})).toBeNull()
    expect(parseMesocycle(null)).toBeNull()
  })

  it('filters non-string entries in the list fields', () => {
    const parsed = parseMesocycle(payload({ focus: ['chest', 3], notes: [1, 'ok'] }))
    expect(parsed?.focus).toEqual(['chest'])
    expect(parsed?.notes).toEqual(['ok'])
  })

  it('derives the total sets when the field is missing', () => {
    const parsed = parseMesocycle(payload({ total_sets: undefined }))
    expect(parsed?.total_sets).toBe(24)
  })
})

describe('phase helpers', () => {
  it('translates the known phases', () => {
    expect(phaseLabel('accumulation')).toBe('积累')
    expect(phaseLabel('deload')).toBe('减量')
  })

  it('falls back for unknown phases', () => {
    expect(phaseLabel('mystery')).toBe('mystery')
    expect(phaseLabel(null)).toBe('—')
  })

  it('maps the phase to a tone', () => {
    expect(phaseTone('deload')).toBe('rest')
    expect(phaseTone('realization')).toBe('peak')
    expect(phaseTone('nope')).toBe('build')
  })
})

describe('text helpers', () => {
  it('formats a slot', () => {
    expect(slotText(parseMesocycleSlot(slot())!)).toBe('4 组 × 8 次 · 62.5 kg')
  })

  it('omits the weight when there is none', () => {
    expect(slotText(parseMesocycleSlot(slot({ weight: 0 }))!)).toBe('4 组 × 8 次')
  })

  it('formats an exercise with its name', () => {
    expect(exerciseText(parseMesocycleExercise(exercise())!)).toBe('杠铃卧推 3 组 × 8 次 · 62.5 kg')
  })

  it('omits the exercise weight when there is none', () => {
    expect(exerciseText(parseMesocycleExercise(exercise({ weight: 0 }))!)).toBe('杠铃卧推 3 组 × 8 次')
  })

  it('describes the volume', () => {
    expect(volumeHint(1)).toBe('容量满载')
    expect(volumeHint(0.5)).toBe('容量收缩')
    expect(volumeHint(null)).toBe('容量 —')
  })

  it('describes the intensity', () => {
    expect(intensityHint(0.72)).toBe('强度 72%')
    expect(intensityHint(0)).toBe('强度 —')
  })

  it('describes the autoregulation discount', () => {
    expect(autoregulationText(1)).toBe('容量正常')
    expect(autoregulationText(0.8)).toBe('容量下调 20%')
  })
})

describe('week helpers', () => {
  it('finds the heaviest week', () => {
    const parsed = parseMesocycle(payload())!
    expect(heaviestWeek(parsed.weeks)?.index).toBe(1)
  })

  it('finds the deload week', () => {
    const parsed = parseMesocycle(payload())!
    expect(deloadWeek(parsed.weeks)?.index).toBe(2)
  })

  it('returns null when there is nothing to find', () => {
    expect(heaviestWeek([])).toBeNull()
    expect(deloadWeek([])).toBeNull()
  })
})

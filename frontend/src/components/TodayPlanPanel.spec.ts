// @vitest-environment happy-dom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import TodayPlanPanel from './TodayPlanPanel.vue'
import { parseMesocycle } from '../utils/periodization'

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
    note: '容量最高、强度最低',
    volume: 1,
    intensity: 0.72,
    reps_low: 8,
    reps_high: 12,
    rir: 3,
    total_sets: 16,
    sessions: [
      session(),
      session({ index: 2, label: '第 2 天', slots: [slot({ exercises: [] })] }),
    ],
    ...overrides,
  }
}

function payload(overrides: Record<string, unknown> = {}) {
  return {
    weeks: [week()],
    days_per_week: 2,
    readiness: 88,
    focus: ['chest'],
    avoid: [],
    autoregulation: 1,
    notes: [],
    total_weeks: 1,
    total_sets: 16,
    ...overrides,
  }
}

describe('TodayPlanPanel', () => {
  it('renders nothing without a plan', () => {
    const wrapper = mount(TodayPlanPanel, { props: { plan: null } })
    expect(wrapper.find('.today-plan').exists()).toBe(false)
  })

  it('shows the phase and the day label', () => {
    const wrapper = mount(TodayPlanPanel, {
      props: { plan: parseMesocycle(payload()), weekday: 1 },
    })
    expect(wrapper.find('.phase-tag').text()).toBe('积累')
    expect(wrapper.find('.today-phase strong').text()).toBe('第 1 天')
  })

  it('picks the training day that matches the weekday', () => {
    const wrapper = mount(TodayPlanPanel, {
      props: { plan: parseMesocycle(payload()), weekday: 2 },
    })
    expect(wrapper.find('.today-phase strong').text()).toBe('第 2 天')
  })

  it('wraps around when the weekday exceeds the training days', () => {
    const wrapper = mount(TodayPlanPanel, {
      props: { plan: parseMesocycle(payload()), weekday: 5 },
    })
    expect(wrapper.find('.today-phase strong').text()).toBe('第 1 天')
  })

  it('lists the exercises of the day', () => {
    const wrapper = mount(TodayPlanPanel, {
      props: { plan: parseMesocycle(payload()), weekday: 1 },
    })
    const items = wrapper.findAll('.today-exercise')
    expect(items).toHaveLength(1)
    expect(items[0]?.text()).toContain('杠铃卧推')
    expect(items[0]?.text()).toContain('62.5 kg')
  })

  it('tags the exercises that come from an e1RM estimate', () => {
    const wrapper = mount(TodayPlanPanel, {
      props: { plan: parseMesocycle(payload()), weekday: 1 },
    })
    expect(wrapper.find('.exercise-tag').text()).toBe('e1RM 折算')
  })

  it('explains a rest day when there are no exercises', () => {
    const wrapper = mount(TodayPlanPanel, {
      props: { plan: parseMesocycle(payload()), weekday: 2 },
    })
    expect(wrapper.find('.today-exercises').exists()).toBe(false)
    expect(wrapper.find('.today-empty').text()).toContain('恢复日')
  })

  it('shows the rep range and the capacity discount', () => {
    const wrapper = mount(TodayPlanPanel, {
      props: { plan: parseMesocycle(payload()), weekday: 1 },
    })
    const meta = wrapper.find('.today-meta').text()
    expect(meta).toContain('8–12 次')
    expect(meta).toContain('容量正常')
  })

  it('applies the tone of the phase', () => {
    const wrapper = mount(TodayPlanPanel, {
      props: {
        plan: parseMesocycle(payload({ weeks: [week({ phase: 'deload' })] })),
        weekday: 1,
      },
    })
    expect(wrapper.find('.today-plan').classes()).toContain('tone-rest')
  })
})

// @vitest-environment happy-dom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import MesocyclePanel from './MesocyclePanel.vue'
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
    weeks: [
      week(),
      week({
        index: 2,
        phase: 'deload',
        label: '减量',
        volume: 0.5,
        intensity: 0.6,
        total_sets: 8,
        sessions: [session({ index: 1, label: '第 2 天' })],
      }),
    ],
    days_per_week: 4,
    readiness: 88,
    focus: ['chest'],
    avoid: ['legs'],
    autoregulation: 1,
    notes: ['容量已按准备度调整'],
    total_weeks: 2,
    total_sets: 24,
    ...overrides,
  }
}

describe('MesocyclePanel', () => {
  it('renders nothing without a plan', () => {
    const wrapper = mount(MesocyclePanel, { props: { plan: null } })
    expect(wrapper.find('.mesocycle').exists()).toBe(false)
  })

  it('shows the cycle summary', () => {
    const wrapper = mount(MesocyclePanel, { props: { plan: parseMesocycle(payload()) } })
    const summary = wrapper.findAll('.summary-item')
    expect(summary).toHaveLength(4)
    expect(summary[0]?.text()).toContain('准备度')
    expect(summary[0]?.text()).toContain('88')
  })

  it('renders one bar per week', () => {
    const wrapper = mount(MesocyclePanel, { props: { plan: parseMesocycle(payload()) } })
    expect(wrapper.findAll('.cycle-bar')).toHaveLength(2)
  })

  it('opens on the first week', () => {
    const wrapper = mount(MesocyclePanel, { props: { plan: parseMesocycle(payload()) } })
    expect(wrapper.find('.cycle-week-head h4').text()).toContain('第 1 周')
    expect(wrapper.find('.cycle-week-head h4').text()).toContain('积累')
  })

  it('switches weeks when a bar is clicked', async () => {
    const wrapper = mount(MesocyclePanel, { props: { plan: parseMesocycle(payload()) } })
    const bars = wrapper.findAll('.cycle-bar')
    await bars[1]?.trigger('click')
    expect(wrapper.find('.cycle-week-head h4').text()).toContain('第 2 周')
    expect(wrapper.find('.cycle-week-head h4').text()).toContain('减量')
  })

  it('lists the training days of the week', () => {
    const wrapper = mount(MesocyclePanel, { props: { plan: parseMesocycle(payload()) } })
    expect(wrapper.findAll('.cycle-day')).toHaveLength(1)
    expect(wrapper.find('.cycle-day-head strong').text()).toBe('第 1 天')
  })

  it('renders each slot with its volume', () => {
    const wrapper = mount(MesocyclePanel, { props: { plan: parseMesocycle(payload()) } })
    const detail = wrapper.find('.slot-detail').text()
    expect(detail).toContain('4 组')
    expect(detail).toContain('8 次')
    expect(detail).toContain('62.5 kg')
  })

  it('tags the slots that come from an e1RM estimate', () => {
    const wrapper = mount(MesocyclePanel, { props: { plan: parseMesocycle(payload()) } })
    expect(wrapper.find('.slot-tag').text()).toBe('e1RM 折算')
  })

  it('lists the concrete exercises of each slot', () => {
    const wrapper = mount(MesocyclePanel, { props: { plan: parseMesocycle(payload()) } })
    const items = wrapper.findAll('.slot-exercises li')
    expect(items).toHaveLength(1)
    expect(items[0]?.text()).toContain('杠铃卧推')
    expect(items[0]?.text()).toContain('62.5 kg')
  })

  it('hides the exercise list when the slot has none', () => {
    const wrapper = mount(MesocyclePanel, {
      props: { plan: parseMesocycle(payload({ weeks: undefined })) },
    })
    expect(wrapper.find('.slot-exercises').exists()).toBe(false)
  })

  it('shows the notes when there are any', () => {
    const wrapper = mount(MesocyclePanel, { props: { plan: parseMesocycle(payload()) } })
    expect(wrapper.find('.cycle-notes').text()).toContain('容量已按准备度调整')
  })

  it('hides the notes block when there is nothing to say', () => {
    const wrapper = mount(MesocyclePanel, { props: { plan: parseMesocycle(payload({ notes: [] })) } })
    expect(wrapper.find('.cycle-notes').exists()).toBe(false)
  })

  it('describes the volume and the intensity of the week', () => {
    const wrapper = mount(MesocyclePanel, { props: { plan: parseMesocycle(payload()) } })
    const meta = wrapper.find('.cycle-week-meta').text()
    expect(meta).toContain('容量满载')
    expect(meta).toContain('强度 72%')
    expect(meta).toContain('8–12 次')
  })
})

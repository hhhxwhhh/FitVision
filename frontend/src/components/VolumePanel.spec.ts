// @vitest-environment happy-dom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import VolumePanel from './VolumePanel.vue'
import { parseVolume } from '../utils/volume'

function muscle(overrides: Record<string, unknown> = {}) {
  return {
    muscle: 'chest',
    label: '胸部',
    sets: 12,
    weeks: 4,
    tonnage: 24000,
    intensity_volume: 16800,
    effective_volume: 16800,
    share: 0.5,
    status: 'ok',
    ...overrides,
  }
}

function report(overrides: Record<string, unknown> = {}) {
  return {
    available: true,
    reason: '',
    days: 56,
    weeks: 8,
    sessions: [
      {
        date: '2026-03-01',
        sets: 16,
        measurable_sets: 14,
        tonnage: 6400,
        intensity_volume: 4480,
        effective_volume: 4400,
      },
    ],
    weekly: [
      {
        year: 2026,
        week: 9,
        sessions: 3,
        sets: 24,
        measurable_sets: 20,
        tonnage: 12000,
        intensity_volume: 8400,
        effective_volume: 8200,
      },
      {
        year: 2026,
        week: 10,
        sessions: 3,
        sets: 26,
        measurable_sets: 22,
        tonnage: 14000,
        intensity_volume: 9800,
        effective_volume: 9600,
      },
    ],
    muscles: [
      muscle(),
      muscle({ muscle: 'back', label: '背部', share: 0.35, status: 'low' }),
    ],
    total_tonnage: 38000,
    total_intensity_volume: 26600,
    total_effective_volume: 26000,
    concentration: 0.2,
    trend: 'rising',
    trend_slope: 0.03,
    verdict: '容量稳步上升',
    advice: [],
    ...overrides,
  }
}

describe('VolumePanel', () => {
  it('renders nothing without a report', () => {
    const wrapper = mount(VolumePanel, { props: { report: null } })
    expect(wrapper.find('.volume').exists()).toBe(false)
  })

  it('shows the summary numbers', () => {
    const wrapper = mount(VolumePanel, { props: { report: parseVolume(report()) } })
    const summary = wrapper.find('.volume-summary').text()
    expect(summary).toContain('有效容量')
    expect(summary).toContain('容量分布均衡')
    expect(summary).toContain('稳步上升')
    expect(summary).toContain('容量稳步上升')
  })

  it('renders one row per muscle', () => {
    const wrapper = mount(VolumePanel, { props: { report: parseVolume(report()) } })
    const rows = wrapper.findAll('.volume-muscle')
    expect(rows).toHaveLength(2)
    expect(rows[0]?.text()).toContain('胸部')
    expect(rows[1]?.text()).toContain('背部')
  })

  it('shows the muscle status label', () => {
    const wrapper = mount(VolumePanel, { props: { report: parseVolume(report()) } })
    const rows = wrapper.findAll('.volume-muscle')
    expect(rows[0]?.text()).toContain('正常')
    expect(rows[1]?.text()).toContain('偏低')
  })

  it('renders a bar per week', () => {
    const wrapper = mount(VolumePanel, { props: { report: parseVolume(report()) } })
    expect(wrapper.findAll('.week-bar')).toHaveLength(2)
  })

  it('lists the advice when the backend gives it', () => {
    const payload = report({ advice: ['容量全在胸部。'] })
    const wrapper = mount(VolumePanel, { props: { report: parseVolume(payload) } })
    expect(wrapper.find('.volume-advice').text()).toContain('容量全在胸部')
  })

  it('hides the advice block when there is none', () => {
    const wrapper = mount(VolumePanel, { props: { report: parseVolume(report()) } })
    expect(wrapper.find('.volume-advice').exists()).toBe(false)
  })

  it('lists every training day in the detail section', () => {
    const payload = report({
      sessions: [
        {
          date: '2026-03-01',
          sets: 16,
          measurable_sets: 14,
          tonnage: 6400,
          intensity_volume: 4480,
          effective_volume: 4400,
        },
        {
          date: '2026-03-04',
          sets: 12,
          measurable_sets: 10,
          tonnage: 4200,
          intensity_volume: 2940,
          effective_volume: 2900,
        },
      ],
    })
    const wrapper = mount(VolumePanel, { props: { report: parseVolume(payload) } })
    const items = wrapper.findAll('.detail-list li')
    expect(items).toHaveLength(2)
    expect(items[0]?.text()).toContain('2026-03-01')
  })

  it('shows the empty state when the data is unavailable', () => {
    const payload = report({
      available: false,
      reason: '还没有带重量的训练记录',
      muscles: [],
    })
    const wrapper = mount(VolumePanel, { props: { report: parseVolume(payload) } })
    expect(wrapper.find('.volume-empty').text()).toContain('重量')
    expect(wrapper.find('.volume').exists()).toBe(false)
  })

  it('marks a falling trend with the danger tone', () => {
    const payload = report({ trend: 'falling' })
    const wrapper = mount(VolumePanel, { props: { report: parseVolume(payload) } })
    expect(wrapper.find('.tone-down').exists()).toBe(true)
  })
})

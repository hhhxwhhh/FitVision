// @vitest-environment happy-dom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import IntensityPanel from './IntensityPanel.vue'
import { parseIntensity } from '../utils/intensity'

function zone(key: string, overrides: Record<string, unknown> = {}) {
  return {
    key,
    label: '',
    sets: 4,
    share: 0.25,
    target_share: 0.25,
    deviation: 0,
    load: 300,
    ...overrides,
  }
}

function session(overrides: Record<string, unknown> = {}) {
  return {
    date: '2026-03-01',
    sets: 16,
    zones: [
      zone('zone_1', { sets: 2, share: 0.125 }),
      zone('zone_2', { sets: 8, share: 0.5 }),
      zone('zone_3', { sets: 4, share: 0.25 }),
      zone('zone_4', { sets: 2, share: 0.125 }),
    ],
    rpe_trimp: 1200,
    intensity_trimp: 1300,
    high_intensity_sets: 2,
    balanced: true,
    notes: [],
    ...overrides,
  }
}

function report(overrides: Record<string, unknown> = {}) {
  return {
    available: true,
    reason: '',
    days: 28,
    weeks: 4,
    sessions: [session()],
    weekly: [],
    balance_score: 0.92,
    verdict: '分布良好',
    advice: [],
    ...overrides,
  }
}

describe('IntensityPanel', () => {
  it('renders nothing without a report', () => {
    const wrapper = mount(IntensityPanel, { props: { report: null } })
    expect(wrapper.find('.intensity').exists()).toBe(false)
  })

  it('shows the summary numbers', () => {
    const wrapper = mount(IntensityPanel, { props: { report: parseIntensity(report()) } })
    const summary = wrapper.find('.intensity-summary').text()
    expect(summary).toContain('强度分布很均衡')
    expect(summary).toContain('高强度组')
  })

  it('renders one row per intensity zone', () => {
    const wrapper = mount(IntensityPanel, { props: { report: parseIntensity(report()) } })
    const rows = wrapper.findAll('.intensity-zone')
    expect(rows).toHaveLength(4)
    expect(rows[0]?.text()).toContain('恢复')
    expect(rows[3]?.text()).toContain('强度')
  })

  it('shows the target share as a reference line', () => {
    const wrapper = mount(IntensityPanel, { props: { report: parseIntensity(report()) } })
    expect(wrapper.findAll('.zone-target').length).toBe(4)
  })

  it('lists the advice when the backend gives it', () => {
    const payload = report({ advice: ['高强度占比偏高。'] })
    const wrapper = mount(IntensityPanel, { props: { report: parseIntensity(payload) } })
    expect(wrapper.find('.intensity-advice').text()).toContain('高强度占比偏高')
  })

  it('hides the advice block when there is none', () => {
    const wrapper = mount(IntensityPanel, { props: { report: parseIntensity(report()) } })
    expect(wrapper.find('.intensity-advice').exists()).toBe(false)
  })

  it('lists every training day in the detail section', () => {
    const payload = report({
      sessions: [session(), session({ date: '2026-03-04', balanced: false })],
    })
    const wrapper = mount(IntensityPanel, { props: { report: parseIntensity(payload) } })
    const items = wrapper.findAll('.detail-list li')
    expect(items).toHaveLength(2)
    expect(items[0]?.text()).toContain('2026-03-01')
    expect(items[1]?.text()).toContain('强度偏高')
  })

  it('shows the empty state when the data is unavailable', () => {
    const payload = report({
      available: false,
      reason: '还没有带重量或 RPE 的训练记录',
      sessions: [],
    })
    const wrapper = mount(IntensityPanel, { props: { report: parseIntensity(payload) } })
    expect(wrapper.find('.intensity-empty').text()).toContain('RPE')
    expect(wrapper.find('.intensity').exists()).toBe(false)
  })

  it('counts the unbalanced sessions in the summary', () => {
    const payload = report({
      sessions: [session(), session({ balanced: false }), session({ balanced: false })],
    })
    const wrapper = mount(IntensityPanel, { props: { report: parseIntensity(payload) } })
    expect(wrapper.find('.intensity-summary').text()).toContain('失衡训练')
  })
})

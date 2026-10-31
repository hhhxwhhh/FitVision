// @vitest-environment happy-dom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import MuscleRecoveryPanel from './MuscleRecoveryPanel.vue'
import type { MuscleRecoveryState } from '../utils/muscleRecovery'

function state(overrides: Partial<MuscleRecoveryState> = {}): MuscleRecoveryState {
  return {
    muscle: 'chest',
    label: '胸部',
    residual: 0,
    recovery: 100,
    status: 'ready',
    hours_to_ready: 0,
    weekly_sets: 14,
    volume_status: 'optimal',
    multiplier: 1.15,
    ...overrides,
  }
}

const sample = [
  state({ muscle: 'legs', label: '腿部', recovery: 32, status: 'fatigued', hours_to_ready: 96, multiplier: 0.7 }),
  state({ muscle: 'back', label: '背部', recovery: 70, status: 'caution', weekly_sets: 4, volume_status: 'under' }),
  state(),
]

describe('MuscleRecoveryPanel', () => {
  it('renders one row per muscle group', () => {
    const wrapper = mount(MuscleRecoveryPanel, { props: { states: sample } })
    expect(wrapper.findAll('.muscle-row')).toHaveLength(3)
  })

  it('sorts the sorest muscle to the top', () => {
    const wrapper = mount(MuscleRecoveryPanel, { props: { states: sample } })
    expect(wrapper.find('.muscle-row .muscle-name').text()).toBe('腿部')
  })

  it('marks the tone of each row from its recovery', () => {
    const wrapper = mount(MuscleRecoveryPanel, { props: { states: sample } })
    const rows = wrapper.findAll('.muscle-row')
    expect(rows[0]?.classes()).toContain('tone-fatigued')
    expect(rows[1]?.classes()).toContain('tone-caution')
    expect(rows[2]?.classes()).toContain('tone-ready')
  })

  it('fills the bar proportionally to the recovery', () => {
    const wrapper = mount(MuscleRecoveryPanel, { props: { states: sample } })
    expect(wrapper.find('.muscle-bar-fill').attributes('style')).toContain('32%')
  })

  it('shows the weekly volume and the estimated wait', () => {
    const wrapper = mount(MuscleRecoveryPanel, { props: { states: sample } })
    const hint = wrapper.find('.muscle-row .muscle-hint').text()
    expect(hint).toContain('约 4 天')
    expect(hint).toContain('14 组')
  })

  it('translates the focus and avoid keys into labels', () => {
    const wrapper = mount(MuscleRecoveryPanel, {
      props: { states: sample, focus: ['chest'], avoid: ['legs'] },
    })
    expect(wrapper.find('.advice-go').text()).toContain('胸部')
    expect(wrapper.find('.advice-wait').text()).toContain('腿部')
  })

  it('hides the advice block when there is nothing to say', () => {
    const wrapper = mount(MuscleRecoveryPanel, { props: { states: sample } })
    expect(wrapper.find('.muscle-advice').exists()).toBe(false)
  })

  it('renders nothing without data', () => {
    const wrapper = mount(MuscleRecoveryPanel, { props: { states: [] } })
    expect(wrapper.find('.muscle-recovery').exists()).toBe(false)
  })

  it('survives missing optional props', () => {
    const wrapper = mount(MuscleRecoveryPanel, { props: { states: [state()] } })
    expect(wrapper.findAll('.muscle-row')).toHaveLength(1)
  })
})

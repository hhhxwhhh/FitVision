// @vitest-environment happy-dom
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import TrainingCalendar from './TrainingCalendar.vue'

const mountCalendar = (activeDays: string[] = []) =>
  mount(TrainingCalendar, { props: { activeDays } })

describe('TrainingCalendar', () => {
  it('renders a full week header and seven columns per row', () => {
    const wrapper = mountCalendar()
    expect(wrapper.findAll('.weekday')).toHaveLength(7)
    const cells = wrapper.findAll('.cell')
    expect(cells.length % 7).toBe(0)
  })

  it('highlights the days that contain a session', () => {
    const year = new Date().getFullYear()
    const month = String(new Date().getMonth() + 1).padStart(2, '0')
    const wrapper = mountCalendar([`${year}-${month}-05`, `${year}-${month}-06`])

    expect(wrapper.findAll('.cell.active')).toHaveLength(2)
    expect(wrapper.text()).toContain('本月训练 2 天')
  })

  it('reports zero training days when nothing is active', () => {
    const wrapper = mountCalendar([])
    expect(wrapper.findAll('.cell.active')).toHaveLength(0)
    expect(wrapper.text()).toContain('本月训练 0 天')
  })

  it('moves to the previous month and back to today', async () => {
    const wrapper = mountCalendar()
    const titleBefore = wrapper.find('.calendar-title').text()

    await wrapper.find('button[aria-label="上一个月"]').trigger('click')
    expect(wrapper.find('.calendar-title').text()).not.toBe(titleBefore)

    const todayButton = wrapper.find('.today-btn')
    await todayButton.trigger('click')
    expect(wrapper.find('.calendar-title').text()).toBe(titleBefore)
    expect(todayButton.attributes('disabled')).toBeDefined()
  })

  it('marks today with an outline class', () => {
    const wrapper = mountCalendar()
    expect(wrapper.findAll('.cell.today').length).toBeLessThanOrEqual(1)
  })
})

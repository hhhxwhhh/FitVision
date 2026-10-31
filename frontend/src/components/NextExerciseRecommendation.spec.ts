// @vitest-environment happy-dom
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import NextExerciseRecommendation from './NextExerciseRecommendation.vue'

const { mockGet } = vi.hoisted(() => ({ mockGet: vi.fn() }))
vi.mock('../api', () => ({ default: { get: mockGet } }))

const payload = [
  { id: 11, exercise: { id: 1, name: '哑铃深蹲', image_url: '/a.jpg' }, reason: '强化股四头肌' },
  { id: 12, exercise: { id: 2, name: '平板支撑', image_url: null }, reason: '提升核心稳定' },
]

describe('NextExerciseRecommendation', () => {
  beforeEach(() => {
    mockGet.mockReset()
    mockGet.mockResolvedValue({ data: payload })
  })

  it('stays hidden when there is no previous exercise', async () => {
    const wrapper = mount(NextExerciseRecommendation, { props: { lastExerciseId: undefined } })
    await nextTick()
    expect(wrapper.find('.next-up-card').exists()).toBe(false)
    expect(mockGet).not.toHaveBeenCalled()
  })

  it('loads the sequence prediction for the finished exercise', async () => {
    const wrapper = mount(NextExerciseRecommendation, { props: { lastExerciseId: 7 } })
    await nextTick()
    await nextTick()

    expect(mockGet).toHaveBeenCalledWith('/recommendations/list/get_personalized/?scenario=default&limit=2')
    expect(wrapper.findAll('.mini-rec-item')).toHaveLength(2)
    expect(wrapper.text()).toContain('哑铃深蹲')
    expect(wrapper.text()).toContain('强化股四头肌')
  })

  it('falls back to a placeholder thumbnail when the exercise has no image', async () => {
    const wrapper = mount(NextExerciseRecommendation, { props: { lastExerciseId: 7 } })
    await nextTick()
    await nextTick()
    const images = wrapper.findAllComponents({ name: 'ElImage' })
    expect(images).toHaveLength(2)
    expect(images[0]?.props('src')).toBe('/a.jpg')
    expect(images[1]?.props('src')).toBe('/placeholder.jpg')
  })

  it('emits the picked exercise so the parent can start it', async () => {
    const wrapper = mount(NextExerciseRecommendation, { props: { lastExerciseId: 7 } })
    await nextTick()
    await nextTick()
    const items = wrapper.findAll('.mini-rec-item')
    expect(items).toHaveLength(2)
    await items[0]?.trigger('click')
    expect(wrapper.emitted('select')?.[0]).toEqual([payload[0]?.exercise])
  })

  it('swallows request failures instead of breaking the training screen', async () => {
    mockGet.mockRejectedValue(new Error('boom'))
    const wrapper = mount(NextExerciseRecommendation, { props: { lastExerciseId: 7 } })
    await nextTick()
    await nextTick()
    expect(wrapper.findAll('.mini-rec-item')).toHaveLength(0)
  })
})

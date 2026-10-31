// @vitest-environment happy-dom
import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import BackToTop from './BackToTop.vue'

const SCROLL_HEIGHT = 2000
const VIEWPORT = 500

const setScroll = (top: number) => {
  document.documentElement.scrollTop = top
  window.dispatchEvent(new Event('scroll'))
}

describe('BackToTop', () => {
  it('stays hidden while the page is near the top', async () => {
    Object.defineProperty(document.documentElement, 'scrollHeight', {
      value: SCROLL_HEIGHT,
      configurable: true,
    })
    Object.defineProperty(window, 'innerHeight', { value: VIEWPORT, configurable: true })

    const wrapper = mount(BackToTop, { attachTo: document.body })
    setScroll(10)
    await wrapper.vm.$nextTick()

    expect(wrapper.find('button').isVisible()).toBe(false)
    wrapper.unmount()
  })

  it('appears once the page is scrolled far enough', async () => {
    const wrapper = mount(BackToTop, { attachTo: document.body })
    setScroll(800)
    await wrapper.vm.$nextTick()

    expect(wrapper.find('button').isVisible()).toBe(true)
    wrapper.unmount()
  })

  it('scrolls back to the top when clicked', async () => {
    const scrollTo = vi.fn()
    Object.defineProperty(window, 'scrollTo', { value: scrollTo, configurable: true })

    const wrapper = mount(BackToTop, { attachTo: document.body })
    setScroll(900)
    await wrapper.vm.$nextTick()
    await wrapper.find('button').trigger('click')

    expect(scrollTo).toHaveBeenCalled()
    wrapper.unmount()
  })

  it('removes its scroll listener on unmount', () => {
    const remove = vi.spyOn(window, 'removeEventListener')
    const wrapper = mount(BackToTop, { attachTo: document.body })
    wrapper.unmount()
    expect(remove).toHaveBeenCalledWith('scroll', expect.any(Function))
    remove.mockRestore()
  })
})

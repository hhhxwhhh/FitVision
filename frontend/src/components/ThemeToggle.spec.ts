// @vitest-environment happy-dom
import { afterEach, describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import ThemeToggle from './ThemeToggle.vue'
import { useTheme } from '../composables/useTheme'

describe('ThemeToggle', () => {
  afterEach(() => {
    useTheme().setMode('light')
  })

  it('renders an accessible icon button', () => {
    const wrapper = mount(ThemeToggle)
    const button = wrapper.get('button.theme-toggle')
    expect(button.attributes('aria-label')).toBe('切换主题')
    expect(button.attributes('type')).toBe('button')
  })

  it('labels the button with the theme it will switch to', async () => {
    useTheme().setMode('light')
    const wrapper = mount(ThemeToggle)
    await nextTick()
    expect(wrapper.get('button.theme-toggle').attributes('title')).toBe('切换到深色主题')

    useTheme().setMode('dark')
    await nextTick()
    expect(wrapper.get('button.theme-toggle').attributes('title')).toBe('切换到浅色主题')
  })

  it('applies the picked mode through the dropdown command', async () => {
    const wrapper = mount(ThemeToggle, { attachTo: document.body })
    const dropdown = wrapper.findComponent({ name: 'ElDropdown' })
    expect(dropdown.exists()).toBe(true)

    dropdown.vm.$emit('command', 'dark')
    await nextTick()

    expect(localStorage.getItem('fitvision-theme')).toBe('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(document.documentElement.dataset.theme).toBe('dark')
    wrapper.unmount()
  })
})

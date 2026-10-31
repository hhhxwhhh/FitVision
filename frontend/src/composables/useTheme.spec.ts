// @vitest-environment happy-dom
import { afterEach, describe, expect, it } from 'vitest'
import { useTheme } from './useTheme'

const THEME_KEY = 'fitvision-theme'

describe('useTheme', () => {
  afterEach(() => {
    useTheme().setMode('system')
  })

  it('shares a single source of truth across call sites', () => {
    const a = useTheme()
    const b = useTheme()
    a.setMode('dark')
    expect(b.mode.value).toBe('dark')
    expect(b.resolved.value).toBe('dark')
  })

  it('persists the chosen mode and mirrors it onto the document root', () => {
    const { setMode } = useTheme()
    setMode('dark')
    expect(localStorage.getItem(THEME_KEY)).toBe('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(document.documentElement.dataset.theme).toBe('dark')

    setMode('light')
    expect(localStorage.getItem(THEME_KEY)).toBe('light')
    expect(document.documentElement.classList.contains('dark')).toBe(false)
    expect(document.documentElement.dataset.theme).toBe('light')
  })

  it('keeps the meta theme-color in sync with the active palette', () => {
    const meta = document.createElement('meta')
    meta.setAttribute('name', 'theme-color')
    document.head.appendChild(meta)

    useTheme().setMode('dark')
    expect(meta.getAttribute('content')).toBe('#070b16')
    useTheme().setMode('light')
    expect(meta.getAttribute('content')).toBe('#f6f7fb')

    meta.remove()
  })

  it('toggle flips between light and dark from the resolved state', () => {
    const theme = useTheme()
    theme.setMode('light')
    theme.toggle()
    expect(theme.mode.value).toBe('dark')
    theme.toggle()
    expect(theme.mode.value).toBe('light')
  })

  it('resolves the system mode against the OS preference', () => {
    const theme = useTheme()
    theme.setMode('system')
    expect(theme.resolved.value).toBe(window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
  })
})

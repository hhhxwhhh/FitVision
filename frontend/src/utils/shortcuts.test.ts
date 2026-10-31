import { describe, expect, it } from 'vitest'
import { isTypingTarget, resolveLeader, SHORTCUT_GROUPS } from './shortcuts'

const el = (tagName: string, extra: Partial<HTMLElement> = {}) =>
  ({ tagName, isContentEditable: false, ...extra }) as unknown as HTMLElement

describe('isTypingTarget', () => {
  it('detects input, textarea and select elements', () => {
    expect(isTypingTarget(el('INPUT'))).toBe(true)
    expect(isTypingTarget(el('TEXTAREA'))).toBe(true)
    expect(isTypingTarget(el('SELECT'))).toBe(true)
  })

  it('detects contenteditable elements', () => {
    expect(isTypingTarget(el('DIV', { isContentEditable: true }))).toBe(true)
  })

  it('returns false for other elements and null', () => {
    expect(isTypingTarget(el('BUTTON'))).toBe(false)
    expect(isTypingTarget(el('DIV'))).toBe(false)
    expect(isTypingTarget(null)).toBe(false)
  })
})

describe('resolveLeader', () => {
  it('maps letters case-insensitively', () => {
    expect(resolveLeader('h')?.path).toBe('/')
    expect(resolveLeader('T')?.path).toBe('/training')
    expect(resolveLeader('G')?.path).toBe('/growth')
  })

  it('returns null for unknown keys', () => {
    expect(resolveLeader('z')).toBeNull()
    expect(resolveLeader('/')).toBeNull()
  })
})

describe('SHORTCUT_GROUPS', () => {
  it('exposes global and navigation groups with entries', () => {
    expect(SHORTCUT_GROUPS.length).toBeGreaterThanOrEqual(2)
    for (const group of SHORTCUT_GROUPS) {
      expect(group.items.length).toBeGreaterThan(0)
    }
  })
})

import { describe, expect, it } from 'vitest'
import { computeScrollProgress } from './scroll'

describe('computeScrollProgress', () => {
  it('returns 0 at the top', () => {
    expect(computeScrollProgress(0, 2000, 800)).toBe(0)
  })

  it('returns 1 at the bottom', () => {
    expect(computeScrollProgress(1200, 2000, 800)).toBe(1)
  })

  it('returns a proportional value in between', () => {
    expect(computeScrollProgress(600, 2000, 800)).toBeCloseTo(0.5, 5)
  })

  it('clamps out-of-range and non-scrollable content', () => {
    expect(computeScrollProgress(9999, 2000, 800)).toBe(1)
    expect(computeScrollProgress(-50, 2000, 800)).toBe(0)
    expect(computeScrollProgress(100, 800, 800)).toBe(0)
  })
})

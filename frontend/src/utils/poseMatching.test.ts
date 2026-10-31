import { describe, expect, it } from 'vitest'
import { OneEuroFilter, normalizeLandmarks, type Point } from './poseMatching'

// Builds a 33-landmark array (MediaPipe layout) with safe defaults so each test
// can override only the joints it cares about.
const makeLandmarks = (overrides: Record<number, Partial<Point>> = {}): Point[] => {
  const base: Point = { x: 0.5, y: 0.5, z: 0 }
  const arr = Array.from({ length: 33 }, () => ({ ...base }))
  for (const [index, patch] of Object.entries(overrides)) {
    arr[Number(index)] = { ...base, ...patch }
  }
  return arr
}

describe('OneEuroFilter', () => {
  it('returns the first sample unchanged', () => {
    const filter = new OneEuroFilter()
    expect(filter.filter(10, 0)).toBe(10)
  })

  it('produces finite output for a noisy signal', () => {
    const filter = new OneEuroFilter(1.2, 0.02, 1.0)
    let last = filter.filter(5, 0)
    for (let i = 1; i < 60; i++) {
      last = filter.filter(5 + Math.sin(i / 3), i * 16)
    }
    expect(Number.isFinite(last)).toBe(true)
  })

  it('falls back to the last value for non-finite input', () => {
    const filter = new OneEuroFilter()
    filter.filter(4, 0)
    expect(filter.filter(NaN, 16)).toBe(4)
    expect(filter.filter(Infinity, 32)).toBe(4)
  })

  it('ignores out-of-order timestamps without throwing', () => {
    const filter = new OneEuroFilter()
    filter.filter(1, 100)
    expect(() => filter.filter(2, 90)).not.toThrow()
    expect(Number.isFinite(filter.filter(2, 90))).toBe(true)
  })

  it('reset() clears internal state', () => {
    const filter = new OneEuroFilter()
    filter.filter(7, 0)
    filter.reset()
    expect(filter.filter(9, 0)).toBe(9)
  })
})

describe('normalizeLandmarks', () => {
  it('returns the input unchanged when there are too few landmarks', () => {
    const small = Array.from({ length: 10 }, () => ({ x: 1, y: 1, z: 0 }))
    expect(normalizeLandmarks(small)).toBe(small)
  })

  it('returns the input unchanged when shoulder/hip landmarks are missing', () => {
    const landmarks = makeLandmarks()
    ;[11, 12, 23, 24].forEach((i) => {
      landmarks[i] = undefined as unknown as Point
    })
    expect(normalizeLandmarks(landmarks)).toBe(landmarks)
  })

  it('normalizes coordinates relative to the hip and torso length', () => {
    const landmarks = makeLandmarks({
      0: { x: 0.5, y: 0.55, z: 0 },
      11: { x: 0.4, y: 0.3, z: 0 },
      12: { x: 0.6, y: 0.3, z: 0 },
      23: { x: 0.44, y: 0.55, z: 0 },
      24: { x: 0.56, y: 0.55, z: 0 },
    })
    const out = normalizeLandmarks(landmarks)
    const at = (i: number) => out[i] as Point

    // midHip = (0.5, 0.55), torsoLength = 0.25 -> point 0 maps to the origin.
    expect(at(0).x).toBeCloseTo(0, 5)
    expect(at(0).y).toBeCloseTo(0, 5)
    expect(at(0).z).toBeCloseTo(0, 5)

    // Left shoulder (0.4, 0.3): x = (0.4-0.5)/0.25 = -0.4, y = (0.3-0.55)/0.25 = -1.
    expect(at(11).x).toBeCloseTo(-0.4, 5)
    expect(at(11).y).toBeCloseTo(-1, 5)
  })
})

/** Scroll progress in the range [0, 1] for a scroll container. */
export function computeScrollProgress(
  scrollTop: number,
  scrollHeight: number,
  viewportHeight: number,
): number {
  const max = scrollHeight - viewportHeight
  if (max <= 0) return 0
  return Math.min(1, Math.max(0, scrollTop / max))
}

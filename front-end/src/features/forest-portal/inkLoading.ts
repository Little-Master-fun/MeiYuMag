// The white ink regions are unioned by an SVG alpha mask. Their uneven edges
// overlap as real loading progresses; no noise animation or second WebGL scene.
export const inkSeeds = [
  [265, 220, 0], [295, 195, 5], [237, 254, 11], [327, 237, 17],
  [280, 286, 23], [201, 205, 29], [338, 171, 35], [181, 288, 41],
  [383, 267, 47], [219, 134, 53], [320, 103, 59], [148, 230, 65],
  [404, 198, 71], [251, 338, 77], [370, 331, 81], [155, 138, 85],
] as const

export const MIN_INK_LOADING_MS = 2000

export function inkFinishDelay(elapsed: number, reduced = false) {
  return Math.max(reduced ? 0 : 300, MIN_INK_LOADING_MS - elapsed)
}

export function inkRadius(progress: number, start: number) {
  return Math.max(0, Math.min(1, (progress - start) / (100 - start))) ** 0.72 * 158
}

export function inkTarget(progress: number, ready: boolean) {
  return ready ? 100 : Math.min(94, Math.max(0, Number.isFinite(progress) ? progress : 0))
}

export function advanceInkProgress(current: number, target: number, elapsed: number, reduced = false) {
  return Math.max(current, reduced ? target : Math.min(target, current + Math.min(64, elapsed) * 0.065))
}

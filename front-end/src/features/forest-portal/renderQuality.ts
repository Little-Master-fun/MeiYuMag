/** Keep reading crisp without raising the GPU cost of camera flights. */
export function scenePixelRatio(
  width: number,
  height: number,
  devicePixelRatio: number,
  mobile: boolean,
  reading: boolean,
  defaultLimit: number,
) {
  const pixels = Math.max(1, width * height)
  const normalLimit = mobile || pixels > 1_500_000 ? 1.25 : defaultLimit
  // Bound the full-screen framebuffer even on very large/Retina displays.
  const readingLimit = Math.min(2, Math.sqrt(8_000_000 / pixels))
  return Math.min(devicePixelRatio || 1, reading ? readingLimit : normalLimit)
}

/** Canvas layout/hit targets remain in logical pixels; only its backing store grows. */
export function paperTextureScale(devicePixelRatio: number, maxTextureSize: number) {
  return Math.min(Math.max(1, devicePixelRatio || 1), 2, maxTextureSize / 1400)
}

export const IDLE_FRAME_INTERVAL = 1000 / 30
export const VENUE_POSITION_INTERVAL = 1000 / 20
export const CAMERA_READOUT_INTERVAL = 1000 / 10
export const MAX_PIXEL_RATIO = 1.5
// Keep tuning values available without mounting the scene's debug controls.
export const SCENE_DEBUG_ENABLED = false

export const cameraDebug = {
  startX: -0.8613,
  startY: 0.4236,
  startZ: -0.7209,
  startTargetX: -0.0097,
  startTargetY: -0.0263,
  startTargetZ: 0.064,
  endX: -0.4508,
  endY: 0.1559,
  endZ: -0.0408,
  endTargetX: -0.0097,
  endTargetY: -0.0263,
  endTargetZ: 0.064,
  rotationSpeed: 10,
  moveDuration: 3,
}

export const cameraReadout = {
  cameraX: 0,
  cameraY: 0,
  cameraZ: 0,
  targetX: 0,
  targetY: 0,
  targetZ: 0,
  rotationX: 0,
  rotationY: 0,
  rotationZ: 0,
  distance: 0,
}

export const clipboardHomeTransform = {
  x: -0.05,
  y: 0.086,
  z: 0.02,
  rotationX: 0,
  rotationY: 0,
  rotationZ: 0,
  scale: 0.01,
}

export const clipboardDebug = { ...clipboardHomeTransform }

export const postLoginClipboardDebug = {
  x: -0.105,
  y: 0.087,
  z: 0.122,
  rotationX: -3.9,
  rotationY: -24.1,
  rotationZ: -1.6,
  scale: 0.019,
}

export const houseDebug = { scale: 3 }

export const mailboxDebug = {
  x: -0.14,
  y: 0.03,
  z: 0.016,
  rotationX: 0,
  rotationY: 90,
  rotationZ: 0,
  scale: 0.054,
}

export const venueTabDebug = {
  leftX: 5,
  leftY: 0,
  rightX: -5,
  rightY: 0,
  left1Y: 0,
  left2Y: 0,
  left3Y: 0,
  left4Y: 0,
  left5Y: 0,
  right1Y: 0,
  right2Y: 0,
  right3Y: 0,
  right4Y: 0,
}

export const postLoginMotionDebug = { overlapDuration: 1.2 }

export const applicationMotionDebug = {
  cameraDelay: 0.2,
  cameraDuration: 1.9,
  clipboardDelay: 0.1,
  clipboardDuration: 1.25,
}

export const submissionEnvelopeDebug = {
  x: -0.012,
  y: 0,
  z: -0.039,
  rotationX: 137,
  rotationY: 0,
  rotationZ: -180,
  scale: 0.02,
  flyDuration: 0.9,
  returnDuration: 0.9,
  successHold: 1.05,
  startAdvance: 0.6,
}

export const submissionSignDebug = {
  maxWidthPx: 850,
  sideInsetPx: 48,
  heightRatio: 0.28,
  z: -0.2,
  topInsetPx: 22,
}

export const pushedTreeDebug = {
  enabled: true,
  treeAmplitude: 0.4,
  directionalLean: 0.5,
  speed: 0.48,
  raccoonAmplitude: 0.4,
  raccoonLean: 1.1,
  raccoonTravel: 0.35,
}

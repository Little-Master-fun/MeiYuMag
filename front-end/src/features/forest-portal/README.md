# Forest portal feature

This directory owns the login-to-application 3D experience. The route view in
`src/views/Login.vue` is intentionally only an entry point.

- `ForestPortal.vue`: coordinates Three.js scene objects, camera transitions,
  DOM overlays, and the feature lifecycle.
- `composables/usePortalAuth.ts`: login, registration, CAPTCHA, and SMS state.
- `composables/useVenueBoards.ts`: personal-home and venue-calendar data state.
- `scene/`: reusable Three.js model/material/animation helpers.
- `submission.ts`: staged-file validation and submission API workflow.
- `api.ts`: feature HTTP reads.
- `config.ts`: scene and debug defaults.
- `types.ts`: shared feature contracts.
- `utils.ts`: date and display helpers.
- `mobileLayout.ts`: shared mobile breakpoint and viewport-based 3D envelope
  placement; pure calendar day/occupancy helpers covered by unit tests.
- `mobile.css`: scoped phone/tablet, safe-area and short-landscape layouts.
- `components/MobileFolder.vue`: touch-scrollable parchment home and calendar,
  sharing `useVenueBoards` data and the existing application/upload workflow.

When adding a new portal capability, keep network/business state in a composable
or service and leave `ForestPortal.vue` responsible for orchestration only.

## Mobile behavior and regression checks

At widths up to 1024 CSS pixels, use the readable DOM parchment with native
vertical scrolling and horizontally scrollable venue bookmarks. Do not shrink
the desktop canvas text into a phone-sized sheet. The 3D forest, camera sequence,
mailbox and real envelope remain active. Drag/pinch scene controls and the debug
panel are disabled on small screens so gestures do not fight page scrolling.

Keep the scene origin identical across viewport sizes: authored camera/prop
keyframes depend on it. Recompute only envelope placement, sign size and overlay
layout on resize; never overwrite the desktop debug coordinates. Mobile device
pixel ratio is capped at 1.25; inactive-scene throttling remains in place.

Validation: run `npm test` and `npm run build`. Check 320×568, 390×844, 430×932,
932×430 and a return to 1440×1000 in touch emulation. Verify:

- Login/register scroll with a reduced visible viewport (software keyboard).
- Home/history scrolling, 31-day calendar, venue switching and future-day apply.
- The 3D envelope is tappable in portrait and landscape; staged files can be
  removed, classified and confirmed before the camera returns to the folder.
- Guide and application dialogs remain scrollable with reachable close/actions.
- Switching back to desktop restores paper-edge bookmarks without position drift.

Upload tests must mock write endpoints: the local backend may have real AI and
SMTP credentials configured. Device emulation does not replace final Safari/
Android real-device checks for keyboards, file pickers and GPU memory limits.

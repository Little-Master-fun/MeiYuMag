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

When adding a new portal capability, keep network/business state in a composable
or service and leave `ForestPortal.vue` responsible for orchestration only.

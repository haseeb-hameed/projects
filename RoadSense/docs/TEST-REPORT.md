# Latest native 2.5.1 saved-DEMO persistence validation

Mobile-only change: clean npm ci, dependency alignment, Expo Doctor **20/20**, **25 native tests**, Android Hermes export **766 modules / 2.2 MB** passed. Storage tests use a fake AsyncStorage backing; App integration mocks native APIs, routes and AI fixtures. It exercises route A -> B, fixed coordinates, vehicle reset, route clearing, fresh store/App remount, fit-all and confirmed individual deletion. Real Android persistence, camera/maps and installed APK remain untested; no backend/browser rerun for this patch.

Audit: 3 high / 5 low. Logs: SAVED-DEMO-VALIDATION.txt, SAVED-DEMO-AUDIT.json. See ../SAVED-POTHOLES-GUIDE.md for phone storage scope, uninstall/clear-data limits and old-record recovery limitations. Older evidence below is historical.

---

# Current 2.5 media-report validation

See ../MEDIA-REPORT-GUIDE.md for exact scope, security/storage policy and Windows update steps. Passed: **38 backend tests**, **15 native helper/serializer/mocked React UI tests**, clean npm ci, SDK dependency alignment, **Expo Doctor 20/20**, Android Hermes export **757 modules / 2.1 MB**. Logs: MEDIA-BACKEND-TESTS.txt, MEDIA-NATIVE-VALIDATION.txt; audit: MEDIA-NATIVE-AUDIT.json (three high).

AI results are mocked in new API/UI tests; real ffmpeg MP4 decoding/duration and JPEG processing are tested. Physical phone gallery/player, new File uploads, actual camera cancellation resolution, live phone-to-model workflow, Windows FFmpeg execution and installed APK remain untested. Browser tests were not rerun. Existing older checks below are historical and do not establish new device performance.

---

# RoadSense — validation evidence

## Current native 2.3.1 camera/map/presentation update

- Clean `npm ci --legacy-peer-deps`, SDK dependency check and Expo Doctor **21/21** passed under Node 22.23.4.
- **12 native helper/contract tests** passed: five original helpers, four route interpolation/demo-gate tests, three upload/endpoint-contract tests. The installed SDK's real multipart serializer reproduces the rejected URI-object error and accepts File-like bytes. Native Android File I/O is not tested by Node.
- **26 backend tests passed** (one existing Starlette/httpx deprecation warning). No backend behavior changes in this update.
- Android Hermes export passed: **705 modules, 1.9 MB**. This is bundling, not an APK build.
- Exact embedded Leaflet HTML browser smoke passed: nine actual OSM tiles loaded, route/start/end/demo/vehicle overlays rendered, vectors remained visible when tiles were deliberately blocked, no page JS errors. This is not native Android WebView testing.
- Mocked React UI smoke passed: start/destination -> selected route -> presentation -> two model-result fixtures -> on-route local report -> dedup -> reset, without community-write calls. Camera, native modules and inference results were mocked; existing React list-key and test-renderer deprecation warnings remain.
- Current mobile audit capture: **four high** entries: @expo/cli, expo, node-forge, zod. Earlier audit counts below are historical. No forced downgrade applied; production security approval is not claimed.
- Physical-phone upload, WebView interaction, permission flow, screen-video detection quality, APK build/install and notification delivery remain unperformed here. See ../CAMERA-MAP-DEMO-FIX.md for presentation data separation and actual limits.

## Earlier SDK 57 migration (native 2.3.0; historical)

- Node 22.23.4; native locked versions Expo 57.0.31, React 19.2.3, React Native 0.86.3, maps 1.27.2.
- Clean `npm ci --ignore-scripts --legacy-peer-deps` passed, verifying manifest/lock alignment.
- `npx expo install --check`: dependencies up to date.
- `npx expo-doctor@latest`: **21/21 checks passed** after consolidating app config.
- SDK 57 `npx expo export --platform android --output-dir android-export-sdk57`: **729 modules, 1.8 MB Android Hermes bundle**, passed. This is not native Gradle/APK compilation or hardware testing.
- Native helper tests: **5 passed**. Backend tests: **26 passed** (one existing Starlette/httpx deprecation warning).
- Safe-area handling migrated to safe-area-context; Google Maps native setup migrated to its config plugin.
- Current native audit: **5 high-severity entries** in Expo tooling: expo, @expo/cli, @expo/code-signing-certificates, node-forge, zod. A non-forced `npm audit fix --ignore-scripts` did not resolve these. Do not use the suggested forced Expo 44 downgrade. Capture: mobile-audit.json. No clean-security claim.
- No physical phone, installed APK, permission-flow, Google Maps display or end-to-end camera/GPS/notification device testing performed. Use PHONE-DEVICE-CHECKLIST.md. Browser tests/build below are historical, not rerun for this SDK-only upgrade.

## Earlier release evidence (historical)

## Passed in this workspace

### Backend logic — 16 pytest tests

`python -m pytest tests/test_backend.py -q`

Covers registration/login/token validation, unauthenticated rejection, input validation, persistent reports, proximity listing, self/duplicate vote protection, clear thresholds, vote changes, heading/accuracy alert filtering, expiry, disaster zones, geometry, Dijkstra/A* correctness, closure-sensitive provider-contract ranking, explicit provider errors, missing-model rejection, invalid images, inference-to-report plumbing, spatial deduplication, and WebSocket events.

These tests use an isolated in-memory SQLite database. Provider and inference responses are mocked where indicated. They are logic tests, not field validation.

### Browser — 2 Playwright tests

`npm test` (backend and Vite must already be running)

1. Registration, live WebSocket connection, coordinate hazard report, rejection of self-confirmation, owner clearance, desktop rendering, phone viewport layout/no horizontal overflow, no page-level JavaScript exceptions.
2. Browser GPS fixture → live Nominatim search for Palakkad Fort → actual OSRM route response displayed in the interface. This test uses a simulated browser position, not a real drive.

Screenshots: browser-desktop.png, browser-phone.png, live-route.png. Map tiles are real OpenStreetMap tiles, not generated screenshots.

### Browser production build

`npm run build` passed. Both package manifests and lockfiles are synchronised. Root `npm audit` reported 0 vulnerabilities in the tested dependency state.

### Native bundle

`cd mobile && npx expo install --check` passed.

`npx expo export --platform android --output-dir android-export` passed (759 modules). This verifies bundling/transformation, not native compilation, installation, camera permissions or map display on a phone.

### Real model smoke

`python scripts/verify_model.py` passed.

`python scripts/smoke_model.py` passed: blank image yielded no detections; the already annotated upstream preview yielded one mapped Pothole box at approximately 0.461 confidence. The running authenticated HTTP inference endpoint also returned this actual detection. Images were not saved by the API.

**Not an accuracy evaluation:** the upstream preview is an annotated montage. No mAP, recall, precision, FPS or local-road safety performance is claimed.

### Live provider checks

- Nominatim place search: responded successfully.
- OSRM real driving route: responded successfully; sample route shape, distance, steps and duration came from the service.
- Nearby hospitals: Nominatim fallback responded successfully after Overpass failed.
- Candidate road-geometry graph fallback: A* and Dijkstra both returned a real 2,247 m candidate path in a sample Palakkad request. The downloaded full OSM graph was not available in this environment. It is explicitly labelled as a candidate-subgraph fallback.

## Not tested / not complete

- Physical Android phone, APK signing/install, Google Maps key setup, native permission prompts, battery/thermal effects and live driving.
- Independent labelled road-image evaluation; rain/night/occlusion performance; multi-hazard model training.
- Full OSM graph retrieval in this environment, PostgreSQL/PostGIS, Docker Compose deployment.
- Remote push, background operation, official disaster warning ingestion: these are not implemented.
- Multi-user load, adversarial security audit, email recovery, production moderation, road/lane-accurate alert matching.

## Known dependency audit issue

After compatible fixes/overrides for PostCSS and image-size, `mobile/npm audit` still reports **4 high-severity entries** in the Expo tooling dependency chain involving `node-forge`, `@expo/cli`, `@expo/code-signing-certificates`, and `expo`. That was the SDK 54 result; mobile-audit.json now records SDK 57 (five high entries including zod). Do not dismiss this as a clean security bill of health. The audit's proposed `--force` solution downgrades Expo to SDK 44 and is not a compatible repair. Reassess/upgrade the SDK and signing-toolchain dependencies before any public or production deployment. No untrusted signing material is processed by this application code.

## Reproduce without contaminating real data

Run API tests first: they use an isolated DB. Browser tests create and clear an explicitly named test report in the running local DB and create disposable test accounts; do not run them against a public production service. Reset the private local DB only after backing it up if necessary.

## Presentation-mode addition

A third Playwright test exercises simulated movement, advance-warning state, simulated confirmation, sample closure, prepared detour, arrival and reset without GPS permission. It asserts that no POST requests are sent to hazard, routing, alert or inference endpoints. Desktop and phone layouts were checked for horizontal overflow.

The separate `RoadSense-Presentation.html` also passed the complete scenario with all HTTP/HTTPS requests blocked and no location permissions. Basemap tiles are unavailable in that offline test, but cached route vectors and scenario controls remain functional. This test does not validate actual driving, live routing or AI detection.

## Video-inference workbench (2.1 update)

- Backend suite now has **18 passing tests**. New coverage checks the read-only frame endpoint without GPS/account, frame ID/threshold/result fields, no report writes, invalid images/thresholds and explicit missing-model errors.
- Browser suite now has **5 passing tests**. New tests open an actual local WebM, send real frames through the running model, pause, resume to the end, restart, and inspect responsive layout with no GPS permissions or road-report writes. A separate image test exercises actual model results on the displayed frame.
- `tests/fixtures/synthetic-decode.webm` is a labelled non-road decode fixture. It is not used to claim pothole accuracy.
- The actual running `/api/vision/frame` endpoint returned two mapped detections on the annotated upstream smoke montage at threshold 0.35. This is inference plumbing evidence, NOT an independent benchmark.
- Read-only preview leaves recorded-video GPS unknown and never creates community reports. The live camera has an optional, separately gated GPS-sharing path.
- This is a browser/backend module; native mobile on-device performance, device camera behaviour, and independent road-video accuracy were not validated here.


## Phone-camera pipeline (2.2 update)

- Backend suite now has **26 passing tests**. Added coverage for phone-session sequencing, account isolation, stop, timestamp/GPS rules, confidence/temporal gate, cooldown, spatial dedup and a synthetic three-frame detection → persisted camera report → another account's proximity-alert response. Inference is mocked in these pipeline tests.
- **5 native helper tests** passed for GPS freshness/accuracy, portrait and landscape letterboxing/box alignment, supported picture-size choice and minimum capture-cycle timing. They do not exercise a phone camera or OS permissions.
- Expo SDK dependency check and Android Hermes bundle export passed with the new DriveCamera component and image manipulation module. This is bundling, not an installed APK or native hardware test.
- Actual `/api/mobile/frame` model smoke returned real boxes on the annotated upstream image in preview-only mode, without GPS and without reports. This is not a field evaluation.
- No physical Android camera, GPS, camera-to-community full device workflow, local notification delivery, Wi-Fi/cellular performance, standalone signing/build, or road test was performed. Use docs/PHONE-DEVICE-CHECKLIST.md.
- That release reported four high-severity Expo-toolchain entries; the current SDK 57 audit above supersedes it. Public production deployment is not approved by these tests.

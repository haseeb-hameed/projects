# Physical Android acceptance checklist — pending execution

Do not mark any item passed merely because Metro exports a bundle. Use a safely parked vehicle or a passenger-operated test setup. Never interact with the phone while driving.

## Setup
- [ ] Record Android version, phone model, Expo SDK/client/build, backend CPU/GPU and network.
- [ ] Verify phone can reach backend health URL and configured weights load.
- [ ] Grant camera, precise foreground location and local notification permissions.
- [ ] Account sign-in and SecureStore persistence work across app restart.
- [ ] Rear camera is used, oriented correctly, with no unsupported picture-size error.

## Frame pipeline
- [ ] Prepare → Start captures automatically with no per-frame user interaction.
- [ ] Measured frame count grows without overlapping requests.
- [ ] Analysed JPEG and returned boxes align for both wide and portrait source images.
- [ ] Main live preview has no stale boxes; analysed-frame panel is clearly labelled.
- [ ] Old temporary files are removed during normal playback; storage does not grow without bound.
- [ ] Stop prevents new captures; server stop response is observed. Already committed reports remain.
- [ ] Tab switch, backgrounding, lock screen and permission revocation stop safely.
- [ ] Network loss/timeouts show an error and stop after repeated failure instead of publishing invented detections.

## GPS/reporting
- [ ] GPS updates remain fresh while standing still and moving (where platform permits).
- [ ] Poor/inaccurate/stale GPS permits preview but creates no report.
- [ ] Preview-only switch creates no reports.
- [ ] Confidence below 0.60 draws a box but does not create a report.
- [ ] A suitable real positive example passes the temporal gate and creates exactly one intended report.
- [ ] Report has actual capture GPS, camera source, timestamp, confidence and Medium/unassessed severity.
- [ ] Nearby repeated detection deduplicates; a different physical hazard is not incorrectly merged (requires field evaluation).

## Second account/device
- [ ] A second account sees the report through live update or refresh.
- [ ] Valid approach position/heading triggers voice and a local notification while foregrounded.
- [ ] Behind-travel-direction report does not trigger when heading is reliable.
- [ ] Unknown heading says nearby, not ahead.
- [ ] Cooldown prevents repeated speech spam.
- [ ] Confirm/clear policy works across accounts and expired/cleared reports stop alerting.

## Evaluation/evidence
- [ ] Use independently annotated footage/images for any claimed precision/recall; do not score the upstream annotated montage.
- [ ] Measure daylight, rain/night and false positives/negatives if claiming them.
- [ ] Record actual round-trip latency, effective FPS and heat/battery behaviour.
- [ ] Retain disclosure that this is backend inference, capture-position GPS and a prototype temporal gate.
- [ ] Do not claim remote push, background monitoring or additional trained hazard classes.

## Native 2.3.1 follow-up (not performed here)

- [ ] Install updated mobile dependencies, restart Metro with --clear and reopen compatible Expo Go.
- [ ] Upload one actual camera File and receive an analysed frame; no FormDataPart error.
- [ ] Pan/pinch OpenStreetMap, choose start/end, draw a route; confirm tile failure notice and route visibility when tiles are unavailable.
- [ ] Enable presentation mode on a selected route; show a clear pothole video to the rear camera.
- [ ] Verify actual model boxes, two-frame demo gate, purple demo marker on selected route, local demo alert list and no community database writes.
- [ ] Verify virtual vehicle approach alert and reset/route-change cleanup.
- [ ] Disable presentation mode; test real GPS-only sharing separately.

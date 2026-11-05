# Implementation status against the submitted abstract

Version 2 is a substantial functional core implementation. **It is not a claim that every proposed research feature is complete or experimentally validated.**

| Abstract area | Implemented in v2 | Remaining / limits |
|---|---|---|
| React Native mobile | Expo Android source; native map, GPS, camera capture, reports, speech, local notifications; bundle compilation passes | No signed APK or physical device/road validation |
| Automatic camera hazard detection | Periodic real frame upload; local YOLO inference; bundled third-party pothole checkpoint; optional auto-report | Potholes only; no locally measured accuracy; other hazard classes require appropriate training/weights |
| Geographical hazard recording | Actual coordinates, severity, timestamps, source, confidence, expiry, deduplication | Camera GPS is capture position, not projected object location; severity is not inferred by model |
| Community verification | Account-level unique vote, own-report confirmation protection, confirmation/clear thresholds | No email verification, abuse moderation, appeal process or account reputation |
| Driver alerts | Distance, heading cone, GPS accuracy gate, foreground voice, local notifications, per-report cooldown | No reliable road/lane matching; no remote push service or background tracking |
| Safe route recommendation | Risk-ranked real OSRM alternatives; closure exclusion; geometry-based report matching | Not globally safest-route optimisation; no traffic/speed safety guarantee |
| Dijkstra / A* | Actual implementations, educational OSM road graph, labelled OSRM geometry graph fallback | OSM graph ignores turn restriction relations; fallback only sees candidate alternatives |
| Disaster-aware routing | Community high-severity closure zones; report-change replanning | No official forecast/live disaster feed; no polygon inundation analysis |
| Hospitals / shelters | OSM Overpass lookup; hospital-only Nominatim fallback | Shelter availability is not guaranteed; occupancy/contact data may be absent |
| PostgreSQL / PostGIS | Configurable SQLAlchemy backend, PostGIS extension, GiST expression index, ST_DWithin query; Compose configuration | Not exercised in this workspace; local tests use SQLite |
| Risk prediction with scikit-learn/XGBoost | Real-data-only scikit-learn training script with grouped holdout evaluation | No labelled risk dataset or trained risk model bundled; runtime route weights are explicit rules, not ML predictions |
| Realtime / JWT | Expiring JWTs and authenticated WebSocket updates | Single-process fan-out; no server-side logout revocation; no refresh-token flow |
| Push notifications | Native local notifications | Remote delivery through Expo/FCM is NOT implemented |

## Readiness conclusion

The project can now demonstrate the connected core workflow: account → real coordinate report → verification → live updates → risk-ranked real route; and camera frame → real pothole inference → optional GPS report. Device testing and local-road evaluation are still essential. Do not present the remaining items as implemented.

For an MCA final review, agree the scope with your supervisor. If every item in the submitted abstract is mandatory, the remaining columns above are still work, not merely paperwork. This software should not be used as a real emergency warning or certified driving navigation system.


## 2.2 phone-camera source update

The native source now uses sequential CameraView capture, resized JPEG upload, server-side temporal/GPS gating and matched-frame boxes. Camera mode activates foreground approach checks and local notifications without requiring a navigation route. It no longer uses the 5.5-second loop. The code and Android Hermes bundle compile, but physical-device testing and APK installation are still pending. This remains backend inference, not on-device inference. No claims about additional hazard classes, remote push or background operation change. See PHONE-CAMERA-GUIDE.md.

## 2.3 SDK 57 native upgrade

Native dependencies and lockfile now target Expo 57.0.31 / React Native 0.86.3 / React 19.2.3. Requires Node >=22.13.0. App configuration is consolidated into app.config.js with the react-native-maps plugin; screen insets use safe-area-context. Expo Doctor passes 21/21 checks; Android Hermes export, 5 native helper tests and 26 backend tests pass. Native APK compilation and physical device tests remain unperformed. Existing SDK 54 clients must be replaced/rebuilt. Five high dependency-audit entries remain in Expo tooling. No additional hazard types, on-device AI, background capture, remote push or safety-validation claims are added.

## 2.3.1 camera, map and route-presentation update

SDK 57 multipart now uses Expo File + expo/fetch instead of unsupported URI objects. Default map uses bundled Leaflet with live OSM tiles in SDK-aligned WebView; no Google key required. Presentation mode uses actual read-only backend frame inference but assigns local-only DEMO reports to an explicitly selected virtual route position. It has route markers, separate demo report list, reset/dedup and virtual vehicle/approach alerts. No virtual coordinates are sent to real community reports; community writes/votes are blocked in presentation mode. These demo markers do not change live route risk ranking. Current test evidence/limits are at the top of TEST-REPORT.md and in CAMERA-MAP-DEMO-FIX.md. No installed Android validation or APK build has been performed.

## 2.5 media evidence and AI review

SDK58 image/video picker and player, private evidence backend, bounded video sampling, optional read-only model analysis, explicitly confirmed real-location review, atomic report/evidence creation and authenticated evidence retrieval/deletion are implemented in source. Presentation file results create local-only virtual route markers after human review; no fictional GPS enters community data. Added backend inference diagnostics and staged camera progress. This does not establish resolution of the user's cancelled-fetch problem without device/backend logs. 38 backend + 15 native tests, Doctor and Android export pass; new hardware/Windows FFmpeg/actual model accuracy testing remains unperformed. See MEDIA-REPORT-GUIDE.md.

## Native 2.5.1 saved DEMO persistence

Phone-local AsyncStorage now durably stores fixed-coordinate presentation potholes. Changing routes clears route/virtual state only; show-all, layer hide/show, individual confirmed delete and separate confirmed delete-all are provided. New-route demo matching uses geometry rather than old route fractions. Existing real community database/evidence policies are untouched. Storage is local to the app/project installation, not cloud/account sync; native Android lifecycle/storage still needs device verification. See SAVED-POTHOLES-GUIDE.md.

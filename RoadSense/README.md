# RoadSense 2.3 — Expo SDK 57 — phone rear-camera detection and GPS reporting

An original navigation-style interface with a FastAPI backend, React browser client, and React Native / Expo Android client. Version 2 replaces the earlier SVG-map demonstration with real coordinates and connected map/routing providers.

**Phone-camera update: [PHONE-CAMERA-GUIDE.md](PHONE-CAMERA-GUIDE.md) covers the native Android rear-camera pipeline and device-test limits.**

**Video module: [VIDEO-DETECTION-GUIDE.md](VIDEO-DETECTION-GUIDE.md) explains actual video analysis, with no GPS or account required for preview.**

**Start here: [SETUP-WINDOWS.md](SETUP-WINDOWS.md).** This source release is a functional core implementation, not a field-validated safety product or a signed Android APK. See [docs/STATUS.md](docs/STATUS.md) before describing it as a completed implementation of every abstract claim.

Native SDK upgrade: **Expo 57.0.31 / React Native 0.86.3 / React 19.2.3**. Requires **Node >=22.13.0**. Start with the phone guide above; use an SDK-57-compatible Expo Go client or rebuild your native app. See [mobile/README.md](mobile/README.md). Backend/browser package versions are unchanged.

## Implemented modules

- **Accounts:** registration, scrypt password hashing, expiring JWTs, authenticated write operations. Android tokens use Expo SecureStore.
- **Real mapping:** Leaflet/OSM browser map, native Android map, foreground GPS, search-on-submit Nominatim destination/start lookup, exact coordinate or map-pin selection. No seeded reports or fake routes.
- **Reports:** actual latitude/longitude, type, severity, timestamp, expiry, source and confidence where applicable. SQLite default; PostgreSQL/PostGIS option with spatial index and proximity query.
- **Verification:** one mutable vote per account per report, self-confirmation blocked, two independent confirmations for confirmed status; owner clearance or two net independent clear votes clears a report.
- **Realtime:** authenticated WebSocket broadcasts plus periodic refresh. Run one API worker in this local version; multiworker fan-out requires Redis or another shared broker.
- **Proximity alerts:** distance and optional direction-of-travel filtering, GPS accuracy gate, five-minute per-hazard speech cooldown. Native local notifications and foreground voice output. Parallel roads can still cause false alerts.
- **Routing:** real OSRM road alternatives ranked by explicit reported-risk penalties. High-severity flood/landslide/blocked-road corridors are excluded from recommendation. No route is guaranteed safe.
- **Dijkstra and A*:** run over a downloaded OSM road graph for trips ≤8 km straight-line. If full graph providers are unavailable, a clearly labelled fallback builds a directed graph from live OSRM alternative geometries; it is not the full road network. No invented graph is substituted.
- **Foreground guidance:** OSRM manoeuvres, simple proximity progression, off-route replan and replan on realtime report changes. Stops on arrival and on rerouting failure. Native guidance stops in background. Not production-grade map matching.
- **Disaster support:** community-reported closures, exclusion zones, mapped nearby hospitals/shelters. No official disaster forecast or shelter occupancy feed.
- **AI inference:** bundled third-party single-class pothole YOLOv8 checkpoint; authenticated in-memory JPEG/PNG processing, confidence/boxes, GPS-tagged optional auto-sharing and spatial/time deduplication. The browser detector now submits sequential frames without a fixed 5.5-second delay. Recorded playback is synchronized to analysed frames. The Android source now has its own sequential rear-camera capture loop, GPS reporting and matched-frame boxes. Both clients use backend inference, not on-device inference. See PHONE-CAMERA-GUIDE.md for test boundaries. Other hazard types are manual unless a compatible custom-trained model is supplied.
- **Research scripts:** detector training/evaluation on a user-provided licensed dataset; optional supervised risk-training pipeline requiring real labelled observations. No synthetic accuracy claims or learned risk model is bundled.

## Layout

```text
backend/             FastAPI, SQLAlchemy persistence, geometry, providers
src/                 Responsive browser UI, real map and camera capture
mobile/              Expo / React Native Android application
models/              Pothole weights, checksum, provenance, upstream card/license
scripts/             Model verification, inference smoke, training/research
 tests/              API and Playwright tests
 docs/               Architecture, status, test report and screenshots
SETUP-WINDOWS.md      Beginner-oriented setup
Dockerfile           Optional web+API container
compose.yaml         Optional PostgreSQL/PostGIS deployment
```

## Quick run

Backend, from project root:

```sh
python -m venv .venv
# Activate your environment (Windows steps are in SETUP-WINDOWS.md).
python -m pip install -r backend/requirements.txt
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8001
```

Another terminal, project root:

```sh
npm ci --legacy-peer-deps
npm run dev
```

Open `http://localhost:5173`; API docs: `http://localhost:8001/docs`. Vite proxies HTTP and WebSockets under `/api` to port **8001**.

For actual AI, install the optional CPU runtime as described in SETUP-WINDOWS.md. Merely having the weights present does not install PyTorch/Ultralytics.

## Reproducibility

Both JavaScript package lockfiles are included and checked for manifest consistency. Do not mix the old v1 lockfile with this release. `npm install --legacy-peer-deps` is a repair alternative if you intentionally edit dependency versions.

```sh
python -m pip install pytest
python -m pytest tests/test_backend.py -q
npm ci --legacy-peer-deps
npx playwright install chromium
# Keep Vite and backend running for browser tests.
npm test
npm run build
```

`tests/test_backend.py` uses an isolated in-memory DB and mocks provider/model responses for logic coverage. `scripts/smoke_model.py` separately executes real model inference. See docs/TEST-REPORT.md for exact evidence and missing validation.

## Operational constraints

Use HTTPS for remote camera, GPS and account traffic. Localhost is allowed by browsers for local development. Mobile LAN HTTP is a development convenience, not safe public deployment. Store environment secrets outside source control. JWTs expire after 24 hours; local sign-out does not revoke already-issued tokens. No email verification or password recovery is implemented.

Public Nominatim is searched on explicit submission only, with caching and upstream throttling. Public OSRM/Overpass/OSM services have no availability guarantee; deploy your own providers for sustained use. Respect OSM and map-tile usage policies, retain attribution, and do not bulk-download tiles. Upstream outages are shown as errors or labelled fallbacks, never synthetic results.

The project is distributed as AGPL-3.0 source because it integrates the Ultralytics ecosystem. The bundled third-party model's repository declares Apache-2.0; retain all model notices. See models/PROVENANCE.md and THIRD-PARTY.md. Commercial deployment requires reviewing the separate dependency/model licensing terms.

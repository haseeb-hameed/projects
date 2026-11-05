# RoadSense 2.3.1 (SDK 57) — use the Android phone's rear camera

**For the latest camera/map fix and video-to-selected-route presentation workflow, read [CAMERA-MAP-DEMO-FIX.md](CAMERA-MAP-DEMO-FIX.md) first.**

This release updates the native React Native / Expo source. It is **not a signed APK**. The Android JavaScript/Hermes bundle was compiled here, but no physical phone, live drive or native permission flow was tested in this workspace.

## What has changed

- New `mobile/src/DriveCamera.js` replaces the old 5.5-second capture interval.
- The phone's **rear camera** captures automatically after one pre-drive start action. The driver does not take or upload individual photos.
- Frames are resized to a maximum 960-pixel edge, then sent sequentially to the authenticated `/api/mobile/frame` endpoint.
- Actual model boxes are displayed on the **exact captured frame**. The separate live camera preview does not have misleading boxes from older frames.
- GPS is attached at capture time. Backend checks timestamp freshness, accuracy, confidence, repeated detections, cooldown and nearby duplicate reports.
- New reports use the existing community database and WebSocket updates.
- Camera mode also activates foreground proximity/heading checks, speech and local notifications for other users' reports, even without a selected navigation route.
- Leaving the Camera tab or backgrounding the app stops capture. An explicit, best-effort stop request also disables the server session. A report already committed is not deleted.

**Inference runs on the backend, not on the phone.** A reachable backend, phone internet/LAN connection and AI runtime are required. Frame rate is displayed, not guaranteed. This is not a 30-FPS or on-device inference implementation.

## SDK 57 upgrade notes

Native source is version 2.3.1: Expo 57.0.31, React 19.2.3, React Native 0.86.3 and react-native-webview 13.16.1 for the default Leaflet/OpenStreetMap map. Use Node >=22.13.0; checks here used 22.23.4. The backend/browser implementation remains unchanged by this SDK-only upgrade.

Use a fresh extraction and install from the included mobile lockfile. Do not reuse SDK 54 `node_modules`, an old QR session, or an existing native development client. Restart Metro with `--clear`; install an SDK-57-compatible Expo Go Android client from the official page. Any custom development client or APK must be rebuilt. Bundling does not prove OS-level compatibility.

## 1. Start the computer backend

Install Python **3.11 or 3.12** and Node.js **22 LTS (22.13.0 or newer)**. Extract the new ZIP into a fresh folder, e.g. `C:\poth\RoadSense-SDK57`.

In a PowerShell terminal at the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.\.venv\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-ai.txt
.\.venv\Scripts\python.exe scripts/verify_model.py
cd backend
..\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8001 --loop asyncio --http h11
```

Leave it running. Check `http://localhost:8001/api/health`. `ai.configured` means weights are present; the first actual inference still needs to load the AI runtime and can be slower.

For your earlier Windows Application Control error, use a supported pure-Python SQLAlchemy install, not disabled security:

```powershell
$env:DISABLE_SQLALCHEMY_CEXT = "1"
..\.venv\Scripts\python.exe -m pip install --force-reinstall --no-cache-dir --no-binary=SQLAlchemy "SQLAlchemy>=2.0,<2.1"
..\.venv\Scripts\python.exe -c "import sqlalchemy; print(sqlalchemy.__version__)"
```

These last commands assume you are in the backend folder. If policy blocks other packages, use an administrator-approved development environment. No security policy bypass is part of this project.

## 2. Connect the phone to the backend

Put Android phone and computer on the same trusted Wi-Fi. Run `ipconfig` on Windows and find the Wi-Fi IPv4 address, e.g. `192.168.1.10`.

Open another terminal at project root:

```powershell
cd mobile
npm.cmd ci --legacy-peer-deps
Copy-Item .env.example .env
```

Edit `mobile\.env`:

```env
EXPO_PUBLIC_API_URL=http://192.168.1.10:8001
```

Replace that address with YOUR computer's IPv4. Do not add `/api`. Do not use localhost on a physical phone.

On the phone's browser, open `http://192.168.1.10:8001/api/health`. If this does not open, solve the Wi-Fi/firewall problem before starting Expo. Allow Python only on your trusted private network; do not disable your firewall globally. Campus Wi-Fi client isolation or a VPN can prevent device-to-computer connections.

LAN HTTP is for private development only. Use HTTPS for deployed operation. If the phone leaves the Wi-Fi area, that LAN backend is no longer reachable; real driving outside the LAN needs a reachable HTTPS backend or a properly tested private hotspot setup.

## 3. Run the native app on Android

The source uses **Expo SDK 57**. Install a compatible Expo Go version from the official Expo Go download page, https://expo.dev/go, or use a compatible development build. A current Expo Go version that does not support SDK 57 cannot open this project unchanged.

From the mobile terminal:

```powershell
npx expo start --clear
```

Open the project through Expo Go's QR scanner. If the network is correct, the app should show the Camera screen. Do not expect this ZIP to install directly like an APK.

### Standalone APK option

You need your own Expo account, a real EAS project ID, signing configuration and a reachable HTTPS API for a standalone build. The current default map uses Leaflet/OpenStreetMap and does not require a Google Maps key.

```powershell
npx eas-cli@latest login
npx eas-cli@latest init
# Use the real project UUID printed by init, not a made-up value.
$env:EAS_PROJECT_ID = "YOUR_REAL_PROJECT_UUID"
npx eas-cli@latest build:configure
npx eas-cli@latest build --platform android --profile preview
```

The app uses a dynamic app.config.js. If the CLI cannot edit it, set EAS_PROJECT_ID locally and in the preview EAS environment, or add the real ID under base.extra.eas.projectId. Also set EXPO_PUBLIC_API_URL in your Expo project's preview cloud environment; local .env/PowerShell alone do not ensure a cloud builder receives it. The supplied preview profile requests APK output. This build has not been executed here; no APK is bundled. Rebuild custom clients for the added WebView dependency.

## 4. Start automatic camera detection (while safely parked)

1. Sign in or create a test account. Do not reuse an important password; no password recovery/email verification is implemented.
2. Open **Camera**. Press **Prepare camera & GPS**.
3. Allow rear-camera and precise foreground location permissions. Allow local notifications when prompted before starting.
4. Wait for the camera to be prepared and for GPS accuracy to reach **50 m or better**. Outdoors generally gives a better fix.
5. Leave **Automatically share GPS-tagged hazards** ON if you want real automatic reporting. Turn it OFF for preview-only analysis.
6. Securely mount the phone with the rear camera observing the road. Do not hold or operate it while driving.
7. Press **Start automatic detection** once, before travelling.
8. The live preview keeps observing the road. The analysed-frame panel displays returned model boxes and confidence. Counts and latency describe actual processed frames.
9. Reports are created automatically only when the server's verification gate passes. You do not manually take photographs or select images.
10. **Stop detection** ends the session; changing tabs or leaving the app also stops it. Resume is manual, not automatic in background.

The gate is intentionally stricter than drawing a box: a detection with confidence 0.45 can be visible but will not create a report under the 0.60 rule. Simple IoU verification across three frames can miss moving hazards, particularly if inference is slow or the object moves rapidly in the image. This policy needs field evaluation and tuning; it is not validated tracking.

## 5. Check sharing and another user's alert

- Saved reports appear in **Alerts**, with capture coordinates, type, time, confidence and source `camera`.
- A second phone/account connected to the SAME backend can see those reports through WebSockets or refresh.
- On the second phone, enable precise GPS and start either camera monitoring or navigation. Reports in the distance/heading filter can produce voice and native local notifications while foregrounded.
- The client ignores reports owned by its current account for approach alerts, to avoid immediately warning about a pothole it just recorded.
- Account-based confirmation and clearance remain available in Alerts.

A stationary classroom demonstration of moving GPS should use the separately labelled presentation simulator; do not invent current GPS coordinates and publish them as real hazards. Actual two-phone hardware alert behaviour still needs testing. Never create fake public road reports for a demonstration.

## Server reporting policy

- Authentication required for native camera frames.
- Unique per-user camera session plus increasing frame sequence.
- Capture timestamp no more than 60 seconds old, no more than 5 seconds in the future; phone automatic date/time should be enabled.
- GPS age at capture ≤30 seconds (up to 2 seconds future tolerance), accuracy ≤50 m, valid coordinates.
- Preview threshold 0.35; auto-report confidence threshold 0.60.
- Three successive overlapping detections of the same type; max five seconds between frames; normalized-box IoU ≥0.20. Only the strongest detection per type is tracked.
- Ten-second per-type cooldown within a session.
- Existing server deduplication for matching type within 25 m / one hour.
- Bad GPS pauses report publication but still allows preview inference. Preview-only mode never publishes.
- The server cannot attest that an arbitrary API client supplied genuine physical GPS/camera data; these are client-reported values.

## Important remaining limits

Only a third-party pothole model is bundled. Cracks, waterlogging, floods, fallen objects and landslides are not automatically detected by it. Confidence is not severity. The report location is the camera capture position, not the projected position of an object ahead. Severity remains **Medium / unassessed**.

The phone uses temporary application-cache JPEGs; old files are deleted during normal processing and on normal screen cleanup. Unexpected process termination may leave cache files for the OS to reclaim. The backend does not store raw frames. Turning sharing off affects subsequent frames; an already submitted or committed report may finish.

No background camera/location service, remote Expo/FCM push delivery, certified navigation, official disaster feed, robust lane matching, offline reporting queue or independent road-accuracy evaluation is implemented. Local notifications require device permission. Camera inference is process-local on the server; use one API worker, or add shared session/broadcast infrastructure before scaling.

## Tests actually performed

- 26 backend tests passed, including stable phone detections → database report → second user's approach alert, GPS gating, confidence filtering, session isolation, stop, ordering, cooldown and deduplication. These reporting tests use **mocked detections/synthetic image frames**, not a physical camera.
- 5 native-helper tests passed for GPS freshness, portrait/landscape box alignment maths, camera-size selection and cycle cadence. These do not exercise a native camera.
- Real-model HTTP smoke returned actual boxes through `/api/mobile/frame` in preview-only mode using an already-annotated upstream montage. This is not an accuracy benchmark.
- Expo dependency check passed and an Android Hermes bundle was exported successfully.
- No physical Android device, standalone APK install, real road drive, native map key, camera permission flow, real GPS accuracy or notification-delivery test was performed here. Complete the checklist in `docs/PHONE-DEVICE-CHECKLIST.md` before a final demonstration.

# SDK 57 camera, map and stationary presentation update (native 2.3.1)

## Install into your existing Windows project (recommended)

This is a mobile-source update. Your existing backend, database, Python environment and mobile/.env do not need to be deleted or reinstalled.

1. Stop Expo with Ctrl+C. Keep the backend running.
2. Back up your current mobile folder (do not publish its .env).
3. Extract **RoadSense-SDK57-Camera-Map-Demo-Fix.zip** into `C:\poth\RoadSense-SDK57`, allowing its `mobile` folder to merge/replace files. You should have `mobile\App.js`, `mobile\src\RoadMap.js` and `mobile\src\DriveCamera.js`.
4. Do NOT extract into the backend folder or create mobile/mobile. The archive does not include or overwrite your .env or database.
5. Run:

```powershell
cd C:\poth\RoadSense-SDK57\mobile
node --version
npm.cmd ci --legacy-peer-deps
npx expo install --check
npx expo start --clear
```

Use Node >=22.13.0 and an SDK-57-compatible Expo Go Android client. Close/reopen Expo Go and scan the NEW QR code. A custom development client/APK must be rebuilt for added native dependencies. This ZIP is source, not an APK.

The backend health URL must still open from your phone. Keep `EXPO_PUBLIC_API_URL` in mobile/.env pointed at the reachable backend origin, without /api. Changing it requires restarting Expo.

## What was fixed

### Upload error: Unsupported FormDataPart implementation

SDK 57's fetch multipart encoder rejects the old React Native `{uri,name,type}` upload object. The camera now appends `new File(jpegUri)` from expo-file-system and uses expo/fetch for multipart requests. Failure messages retain the actual last error instead of replacing it with only a generic network warning. The camera still captures, resizes, uploads sequentially and shows boxes on the matching analysed frame.

### Blank Google map

The default Android map view is replaced with embedded Leaflet/OpenStreetMap in react-native-webview 13.16.1 (SDK-57-aligned). It does not depend on a Google Maps key or Google basemap authorization. Leaflet JS/CSS are bundled locally; only real OSM raster tiles need internet. Route lines/markers render independently of tile availability. If tiles fail, a notice appears and available route vectors remain visible. This is not an offline tile download feature or a repair to Google account credentials.

Map gestures: pan/pinch; tap to choose the current start/destination search target; long-press to open a real-location report when presentation mode is OFF. While presentation mode is ON, map taps do not accidentally clear the selected route.

### Notifications

Includes the earlier startup guard. If expo-notifications cannot load in this Expo Go runtime, the app displays a notice and skips system notifications. Voice and on-screen alerts retain their code paths. This does not supply missing native notification functionality.

## Your stationary presentation workflow

**Safely parked / classroom only. You do not need to physically move.**

1. Open **Navigate**.
2. Choose **Search start**, enter/search a place and select a result. You may use GPS as the start, but presentation mode does not require physical GPS movement.
3. Choose **Search destination**, search and select the destination.
4. Press **Find routes** and select the desired route. The route should be drawn on OpenStreetMap.
5. Press **Enable presentation mode** in the presentation panel. Do not press real Start navigation; presentation has separate virtual-drive controls.
6. Choose the **Detection marker position** with Position −5% / +5%. Default: 25% along the selected route. This is explicitly a virtual location, not the phone's GPS and not inferred from the video.
7. Open **Camera**. Press **Prepare demo camera**, allow camera access, then **Start automatic detection**.
8. Play your pothole video on another phone/laptop/monitor and point this phone's rear camera at it. Avoid glare, make the pothole large/clear, and pause the video briefly if inference is slow.
9. Actual backend pothole inference supplies the boxes. In presentation mode, two overlapping Pothole detections >=0.35 within 15 seconds create a local DEMO report at the chosen route position. No hardcoded example detections are inserted. Screen recapture can reduce detection quality; detection is not guaranteed.
10. You should see **DEMO marker saved on selected route**. The same virtual position is deduplicated within 30 m. To show another marker, change Position +5% and show a detectable pothole again.
11. Press **View route and demo markers**, or open **Navigate**. Purple circles are DEMO reports; the blue point is the virtual vehicle. The route card shows community report count separately from demo marker count. Tap/hold a marker as supported by the WebView to view its label; demo details are also in **Alerts**.
12. Press **Run virtual drive** (0.5% of route per second) or **Vehicle +5%**. Foreground voice/on-screen demo warnings trigger when the virtual vehicle is up to 500 m before a demo marker. These are labelled Presentation only, not actual GPS navigation/ETA. Use small automatic advances if manual 5% steps would jump past a marker.
13. **Reset demo reports / vehicle** clears presentation data. Selecting/recalculating a route also resets the demo. Changing tabs stops camera capture, but demo markers remain for the current app session/route. Reopen Camera and prepare/start again to capture more.

## Data separation — important for your MCA explanation

- Pothole detection: actual model inference on captured camera pixels.
- Demo location: manually chosen virtual position interpolated along the selected route.
- Demo reports: in-memory presentation records only; visible on the route and Alerts tab, not written to the community database or sent to other accounts. They disappear on app reload/reset or route change.
- Presentation inference uses the read-only `/api/vision/frame` endpoint. It does not pass virtual GPS to `/api/mobile/frame` or `/api/hazards`.
- Manual community writes/votes are blocked while presentation mode is enabled. The relaxed demo detection rule is NOT used for real reports.
- To test real community sharing, disable presentation mode, sign in, prepare real GPS and use the real automatic-sharing switch. Real reports use capture GPS, >=0.60 confidence, three stable detections and backend deduplication. They cannot honestly be moved to an arbitrary selected route just because a video depicts a pothole.
- Demo markers are not included in live risk-ranked rerouting and do not prove the selected real route contains a pothole. Virtual alerts only demonstrate the presentation workflow.

## Validation and remaining limits

Passed in this workspace: clean mobile npm ci; Expo dependency check; Expo Doctor 21/21; 12 native helper/serialization/source-contract tests; 26 backend tests; Android Hermes export (705 modules, 1.9 MB). Installed Expo multipart serializer rejects the original URI object and accepts a File-like bytes payload in a Node contract test; this does not exercise Android native File I/O.

Browser smoke of the exact embedded map HTML loaded nine real OSM tiles, rendered route/start/destination/demo/vehicle paths, and kept vector overlays visible when tile requests were deliberately blocked; no page JavaScript errors. A separate mocked React renderer smoke exercised selected start/end -> route -> presentation toggle -> model-result fixtures -> on-route marker -> dedup -> reset without community-write calls. These are not installed Android tests; the UI smoke mocks native modules and inference results.

Physical Android camera/File upload, WebView touch/bridge behavior, video-screen detection accuracy, permission flow, installed APK and notification delivery have NOT been revalidated here. Test on your phone while stationary before presenting. The bundled model is potholes-only; inference is backend-based, not on-device. No certified navigation, independent accuracy/FPS claim, remote push or background capture is added. Current mobile npm audit captures four high Expo-toolchain entries; do not force a downgrade to SDK 44.

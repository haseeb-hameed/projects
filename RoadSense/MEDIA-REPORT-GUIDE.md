# RoadSense 2.5 — SDK 58 photo/video evidence and AI review

This is an UPDATE for your existing RoadSense project, not a fresh complete project or APK. It includes changed backend and mobile source. Keep your existing models, database, .env and Python environment.

## 1. Windows update (both backend and mobile)

1. Stop the backend AND Expo using Ctrl+C in each terminal.
2. Back up the project. With the backend stopped, back up backend/roadsense_v2.sqlite if using the default database. For PostgreSQL, take a proper database backup. Do not publish backups/secrets.
3. Extract **RoadSense-SDK58-Media-Reports-Update.zip** into `C:\poth\RoadSense-SDK57`, merging backend/mobile/docs and replacing files. Do NOT delete those folders or create mobile/mobile. Your folder name can remain SDK57; mobile dependencies use SDK58.
4. Preserve root/backend/mobile .env files, .venv, models/pothole.pt, database and any private_media directory. None are included in the update.
5. Install the updated backend dependencies from project root:

```powershell
cd C:\poth\RoadSense-SDK57
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd backend
..\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8001 --loop asyncio --http h11
```

The new requirement is imageio-ffmpeg for bounded local video inspection/decoding. Existing Torch/Ultralytics requirements remain necessary for AI; they are not replaced by this package. If Windows Application Control blocks the FFmpeg executable, use an administrator-approved environment; do not disable security controls. Photo evidence does not require FFmpeg.

Backend startup creates an additional media_attachments table without deleting the existing hazards/users tables. It is still essential to back up first. `/api/health` should report version **2.5.0** with `media.enabled: true`. If not, you are still running an old backend process/folder.

6. Leave that backend terminal running. In a SECOND PowerShell terminal:

```powershell
cd C:\poth\RoadSense-SDK57\mobile
node --version
npm.cmd ci --legacy-peer-deps
npx expo install --check
npx expo start --clear
```

Use Node 22 LTS >=22.13.0 and SDK-58-compatible Expo Go. Close/reopen Expo Go and scan the new QR. A custom client/APK must be rebuilt for expo-image-picker/expo-video. No signed APK/cloud build is included or tested.

7. Keep mobile/.env pointed at the reachable backend origin, without /api:

```env
EXPO_PUBLIC_API_URL=http://YOUR_COMPUTER_WIFI_IP:8001
```

The phone browser must open that origin plus `/api/health`. Use the same trusted LAN for development and HTTPS for deployed/private media operation. Authentication on plain HTTP does not provide transport confidentiality.

## 2. Real report with image/video evidence

1. Sign in. Turn presentation mode OFF for a real community report.
2. Open **Alerts -> Report / analyse photo or video**. Also available through **+ Report a hazard -> Attach / analyse images or video**, and **Camera -> Choose photo / video instead**.
3. Choose photo or video; review the LOCAL preview first. A photo is prepared as JPEG; video playback has native controls.
4. Read and enable the upload-consent switch, including visibility and metadata warnings.
5. Press **Upload evidence**. It is initially a private draft accessible only to you.
6. You may attach up to 3 items. AI is optional: you can report verified evidence without running AI.
7. Optionally press **Analyse with AI**. The backend uses the existing actual model. Photo analysis returns one analysed frame. Video analysis samples up to 8 frames at roughly four-second intervals; it is not a frame-by-frame whole-video detector.
8. Choose an analysed frame to see its matching image and actual red boxes/confidence. A blank detection list is not proof that the road is safe. Confidence is NOT severity. You can press **Use AI suggestion** but still review everything yourself.
9. Enter the verified actual capture road/landmark and latitude/longitude. Recorded media is NOT assigned current phone GPS automatically. The phone-GPS convenience button is only valid if that is really where the media was captured; it requires a fresh accurate fix.
10. Explicitly confirm the capture-location switch. Select hazard type and manually assessed severity (default Medium).
11. Press **Submit reviewed report with evidence**. This creates the report and evidence association atomically. Analysis alone never posts a hazard.
12. The Alerts tab shows **View image/video evidence** on published reports. Viewing published evidence requires sign-in; normal hazard metadata remains public. Original evidence can include sensitive faces/plates/audio: do not upload media without permission.
13. Owners can delete evidence from active report cards or **Manage my uploaded evidence (including older reports)** in the media form. Deleting evidence does not delete the hazard report.

## 3. Stationary presentation using a file

1. Navigate -> choose start/destination -> Find routes -> select a route.
2. Enable presentation mode and set the desired virtual detection marker position along that route.
3. Sign in and open the media form from Alerts or Camera.
4. Choose, preview, consent and upload evidence; press Analyse with AI.
5. If there is an actual AI Pothole result, review it and press **Add reviewed AI result as local DEMO marker**.
6. A local purple marker is placed at the chosen virtual route position; use virtual-drive controls for approaching warnings. This is human-reviewed file analysis, NOT the camera's two-frame temporal gate.
7. No real community report is written. Uploaded files remain private drafts; reset/reload/route change clears the local demo markers, NOT the uploaded private draft. Use Remove/delete or the evidence manager to delete unwanted uploads.
8. This uses simulated route coordinates, not inferred real coordinates from the media. It does not update live risk-ranked routing or other accounts. It must be explained as a labelled presentation, not a real located road observation.

The automatic rear-camera presentation workflow is also retained and still uses repeated real model detections before creating local markers.

## 4. Camera still shows zero frames / cancelled fetch

The screenshot showed a camera preview but no completed analysis. A working preview does not prove upload or backend inference.

- In Camera, press **Test backend AI before capture** while stopped.
- Step 1 checks API reachability (10 s). Step 2 runs actual blank-image inference (up to 180 s) to expose missing runtime/model problems and warm the model.
- A success verifies BACKEND inference, not camera/File upload or accuracy. Then start capture and watch the stage: Capturing photo -> Resizing JPEG -> Uploading / waiting for backend AI.
- The first successful-analysis wait is now allowed up to 120 s (subsequent frames 45 s). This may help cold starts but does not fix a broken connection.
- If it fails, open the health URL from the phone and inspect the running backend log. From project root, run `.\.venv\Scripts\python.exe scripts\smoke_model.py` in a separate terminal. Send the full error/traceback and connection-check result for further diagnosis.
- Media picker avoids recapturing a video screen but still needs the same reachable backend/AI runtime for analysis. Evidence-only reporting does not require model inference.

## 5. Limits, privacy and storage

- Photo: JPEG/PNG input, max 5 MB and 16 MP on backend; canonical JPEG resized <=1920 with EXIF removed. Mobile prepares photos first.
- Video: modern MP4/MOV, max 20 MB / approximately 30 s; H.264 MP4 recommended. MIME/container/duration/decoding are checked. It is not an antivirus scan. Video audio/metadata may remain.
- Max 3 attachments/report; max 100 stored items or 100 MB/account; global 1 GB/10,000 item quota. Drafts older than 24 h are lazily cleaned on the owner's NEXT upload, not by a background scheduler. Published evidence is retained until explicitly deleted.
- Private storage defaults to backend/private_media. Do not expose this directory as static files or include it in source archives. Back it up with the database when retaining evidence. Optional MEDIA_ROOT changes it.
- Owner-only draft access/analysis/deletion; published active-report evidence visible to authenticated accounts; owners can still view/delete their evidence after report clearance/expiry. No anonymous media URLs.
- No video capture-location/geolocation extraction, face/plate blurring, malware scanning, production moderation, object storage or automatic transcoding. Harden and isolate FFmpeg/media processing before public production use. This remains a single-worker research deployment.
- Stored media-report timestamps represent report creation time, not a verified original capture time. No capture-time extraction is implemented.
- AI remains backend-based and potholes-only. Video sampling and screen recapture can miss hazards. No safety, independent accuracy or FPS guarantee.

## 6. Validation actually performed

- **38 backend tests passed**, including authentication, private media ownership, verified-location enforcement, atomic report association, deletion, metadata stripping, file quotas, cleared-report access, size/type rejection, and real H.264 MP4 creation/FFmpeg decoding/duration checks. AI outputs in these tests are mocked; no new independent model accuracy evaluation was run.
- **15 native tests passed**, including three mocked React UI flows: photo -> consent -> upload -> AI -> location confirmation -> report; demo callback without real-report calls; evidence deletion. Picker/File/player/network are mocked; these are not device tests.
- Clean mobile npm ci, Expo dependency alignment and **Expo Doctor 20/20** passed.
- SDK58 Android Hermes export: **757 modules / approximately 2.1 MB**, passed. Not a native Gradle/APK build.
- Current mobile audit has **three high Expo-toolchain entries**. No forced SDK downgrade was applied.
- Physical Android picker/playback, native File upload, WebView/GPS/permissions, actual phone-to-backend inference, cancelled-fetch resolution and installed APK have NOT been tested here. Browser tests were not rerun. Test while stationary before presenting.

Evidence: docs/MEDIA-BACKEND-TESTS.txt, docs/MEDIA-NATIVE-VALIDATION.txt, docs/MEDIA-NATIVE-AUDIT.json.

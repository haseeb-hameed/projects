# Actual video / camera pothole detection — RoadSense 2.1

## What you can demonstrate while standing still

Select a local road video once. The browser decodes it, samples frames and sends individual JPEGs to the actual local YOLO detector. The analysed frame is displayed with red boxes and labels such as `pothole 0.64`. The scores and boxes are real model responses, not prepared coordinates or animations.

Your `videoplayback.webm` can be selected inside this app even though Arena's chat attachment feature rejects video files. These are different upload/file-selection mechanisms.

## Use the hosted preview in this conversation

1. Open **RoadSense video detector** in the live preview.
2. The **Detection** screen opens by default.
3. Keep **Recorded video** selected and click **Choose road video**.
4. Select your MP4 or WebM from your computer. Prefer unannotated footage; existing boxes/text in a video can influence the detector.
5. Click **Analyse video**. The original source appears in the side panel and the analysed frames with returned boxes appear in the main view.
6. Use **Pause analysis**, **Restart**, or **One frame** as needed.
7. The sampling selector controls frames per SECOND OF SOURCE VIDEO; it does not promise that many processed frames per wall-clock second.
8. The confidence slider applies to the next analysed frame. A lower threshold can expose more false positives.
9. The JSON export button saves the current frame's returned detections. It does not export an annotated movie.

No GPS, login or movement is needed for recorded-video or still-image analysis. No location is inferred from the footage, and no reports are written by recorded-video analysis. The full video is not uploaded; sampled frames are transmitted to the backend, processed in memory, and not retained by the API.

## Live camera

1. Switch to **Live camera** and allow camera access. HTTPS or localhost is required.
2. Click **Enable camera**, then **Analyse camera**.
3. The side preview shows the live source; the main view shows the exact last analysed frame with matching boxes. It is deliberately not an overlay on newer, unprocessed frames.
4. Capture runs sequentially with no overlapping client inference requests and a maximum request cadence of four frames per second. Actual throughput can be much slower. Frames arriving while inference is busy are not queued for live processing; the next capture uses the latest available image.
5. Pause/resume or close the camera from the controls. Processing pauses when the document is hidden.

This is backend inference, not native/on-device inference. It is not a demonstrated 15–30 FPS mobile pipeline. The browser module described here is separate from the newer native phone-camera pipeline. See PHONE-CAMERA-GUIDE.md for the native update.

### Optional automatic live reporting

Only live camera mode offers auto-sharing. It requires an account and an accurate, fresh GPS fix from the main app's location control (Settings → Enable GPS). The client requires a confidence ≥0.60 detection in three successive overlapping analysed frames, then invokes the existing geotagged detector/report endpoint at most once per ten seconds. The server re-runs inference and applies its existing spatial/time report deduplication.

This is a simple temporal filter, not robust object tracking. The re-run can differ slightly from the preview result, and multiple physical potholes can merge into one report. Camera location is the capture GPS, not the projected pothole position; severity defaults to Medium / unassessed. The preview endpoint never writes a report. Do not interact with the phone while driving.

## Run locally on Windows

Use a fresh extracted project folder and Python 3.11/3.12 with Node 22 LTS.

From project root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.\.venv\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-ai.txt
.\.venv\Scripts\python.exe scripts/verify_model.py
cd backend
..\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8001 --loop asyncio --http h11
```

Another terminal, project root:

```powershell
npm.cmd ci --legacy-peer-deps
npm.cmd run dev
```

Open the Vite URL, usually `http://localhost:5173`. Actual inference needs the backend and AI dependencies; unlike the standalone navigation simulation HTML, it cannot run by itself offline.

### If Windows blocks SQLAlchemy compiled extensions

The release pins SQLAlchemy to the 2.0 series. Do not disable Application Control. In the backend terminal, a documented pure-Python build can be used:

```powershell
$env:DISABLE_SQLALCHEMY_CEXT = "1"
..\.venv\Scripts\python.exe -m pip install --force-reinstall --no-cache-dir --no-binary=SQLAlchemy "SQLAlchemy>=2.0,<2.1"
..\.venv\Scripts\python.exe -c "import sqlalchemy; print(sqlalchemy.__version__)"
```

If organisational policy blocks other dependencies, ask the device administrator for an approved Python environment instead of changing the policy.

## Honest limitations

- Bundled weights support potholes only. Cracks, floods and other hazard types still need suitable trained models and evaluation.
- Confidence is not depth, severity, distance or calibrated road-safety certainty.
- Recorded playback advances between analysed frames; it can be slower than the original clip. It intentionally holds the exact frame so boxes do not drift onto later frames.
- No annotated video-file export, native on-device runtime, background camera or field-validated performance is provided by this update.
- Public read-only `/api/vision/frame` is rate-limited and has bounded upload/pixel sizes and limited inference concurrency. Protect it with stronger authentication/quotas before public deployment at scale.
- Browser codec support varies. Try H.264 MP4 or VP8/VP9 WebM. The YouTube player/link itself is not a local video source for this module.

## Validation performed

18 backend tests passed, including read-only no-GPS frame inference and invalid/missing-model checks. Five browser tests passed, including actual WebM decoding and full frame-processing to end, pause/restart, an image inference smoke, and existing navigation/presentation flows. The WebM fixture is explicitly a SYNTHETIC DECODE TEST, not road footage or an accuracy benchmark. The image smoke uses an already-annotated upstream montage and is not an independent accuracy evaluation. No local-road accuracy or live-camera device performance is claimed.

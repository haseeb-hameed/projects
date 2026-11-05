# RoadSense 2.3 (SDK 57) — Windows setup

## Important: use the new ZIP in a fresh folder

Extract **RoadSense-SDK57.zip** to, for example, `C:\poth\RoadSense-SDK57`. Do not copy individual files over the earlier project; old code, ports and lockfiles differ.

Install **Python 3.11 or 3.12**, **Node.js 22 LTS (>=22.13.0)**, and VS Code. During Python installation, tick **Add Python to PATH**. Open the extracted project folder (the one containing package.json) in VS Code.

## A. Run the browser app first

### Terminal 1: backend

Open a PowerShell terminal in the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8001
```

If activation is blocked, switch VS Code's terminal profile to **Command Prompt** and use `.venv\Scripts\activate.bat`, or skip activation and use the root environment Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
cd backend
..\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8001
```

Leave this terminal running. Check `http://localhost:8001/api/health` or `http://localhost:8001/docs`.

### Terminal 2: interface

Open a NEW terminal at the project root, not the backend folder:

```powershell
npm ci --legacy-peer-deps
npm run dev
```

If PowerShell blocks npm.ps1, use `npm.cmd` instead of `npm` or switch to Command Prompt.

Open the printed Vite URL, usually **http://localhost:5173**. Keep both terminals open.

If the lockfile error from v1 reappears, first confirm you extracted the new v2 ZIP. As a repair:

```powershell
npm install --legacy-peer-deps
npm run dev
```

### First journey

1. Sign in → Create an account (use a test password, not an important reused password).
2. Choose **Use GPS**, allowing precise location, or click the start-pin button and select a map point.
3. Type a destination, for example `Palakkad Fort, Kerala`, and press the search button. Choose an actual result.
4. Press **Find routes**. This uses the internet, not preset route shapes.
5. Select a route. **Start navigation** requires an account, a fresh accurate GPS fix, proximity to the route start, and the Road alternatives method.
6. Report a hazard only while safely stopped. Use actual GPS/map coordinates. There are deliberately no example reports in a fresh database.
7. Use a second account in an incognito window to verify a report; self-confirmation is blocked.

The initial map is centred on Palakkad but that centre is **not** a claimed live position. Browser tests use an explicitly simulated GPS fixture, not a live drive.

## B. Enable actual pothole AI

Stop the backend with Ctrl+C. From the project root, with .venv active:

```powershell
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r backend/requirements-ai.txt
python scripts/verify_model.py
python scripts/smoke_model.py
```

The CPU runtime download can be several hundred MB. Inference latency depends on your computer. The pretrained weights are already in `models\pothole.pt`; do not download a generic YOLO/COCO model and expect pothole detection.

Restart the backend:

```powershell
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8001
```

In the browser:

1. Sign in and enable GPS. A fresh fix with accuracy ≤50 m is required.
2. Open **Detection** and allow camera permission.
3. Secure the phone/camera before travelling; do not operate it while driving.
4. Press **Start automatic detection**. Frames are uploaded approximately every 5.5 seconds, without overlapping inference requests.
5. Tick auto-sharing only if you intend to publish GPS-tagged detections. Severity is an unassessed Medium default.
6. Alternatively, select **Test an image** to test a JPEG/PNG, still using a real GPS location.

The third-party model detects **potholes only**. Cracks, flood, waterlogging, obstacles and landslides can be manually reported but are not AI-detected by this checkpoint. Poor results are possible, especially in untested road/weather conditions.

To use another trusted model, set environment variables before starting the API:

```powershell
$env:YOLO_MODEL_PATH = "C:\models\road-hazards\best.pt"
$env:YOLO_CLASS_MAP = '{"D00":"Crack","D10":"Crack","D20":"Crack","D40":"Pothole"}'
```

Those labels are only an example for a model that actually uses them. Never map unrelated classes to hazards.

## C. Run the Android source

The native code compiles to an Android JavaScript/Hermes bundle in the workspace. A signed APK and physical-device road test are **not** supplied.

Keep the backend on port 8001. Put phone and computer on the same trusted Wi-Fi network. On your computer:

```powershell
ipconfig
```

Find the Wi-Fi **IPv4 Address**, e.g. `192.168.1.10`.

From the project root, a new terminal:

```powershell
cd mobile
npm ci --legacy-peer-deps
Copy-Item .env.example .env
```

Edit `mobile\.env`:

```env
EXPO_PUBLIC_API_URL=http://192.168.1.10:8001
```

Use YOUR computer's address. Do not use localhost from a physical phone, and do not append `/api`.

On the phone browser, test `http://192.168.1.10:8001/api/health`. If unreachable, check firewall permission for Python on your **private network**. Do not disable your firewall globally.

Start:

```powershell
npx expo start
```

Open with a compatible **Expo SDK 57** Expo Go version on Android. If your installed Expo Go does not support SDK 57, use a compatible development build or upgrade the SDK carefully; do not randomly force dependency upgrades. `npx expo install --check` verifies the supplied dependency baseline.

### APK build (requires your Expo account and map credentials)

Follow the **Standalone APK option** in [PHONE-CAMERA-GUIDE.md](PHONE-CAMERA-GUIDE.md), including the SDK 57 maps plugin, real EAS project ID, preview cloud environment variables and restricted Maps key. Use a reachable HTTPS backend. Rebuild any old development client/APK; an SDK 54 binary cannot become SDK 57 by receiving JavaScript alone. No signed APK is included and no EAS build was run here.

Native notifications in this release are **local notifications** triggered by foreground proximity checks. Remote push delivery and background tracking are not implemented. Both camera inference and navigation stop when the native app goes to the background.

## D. Optional PostgreSQL / PostGIS

SQLite works without any database server. Do not install PostgreSQL just to try the project.

For the PostGIS deployment option, install Docker Desktop, copy root `.env.example` to `.env`, replace the secrets with random values, then:

```powershell
docker compose up --build
```

Open `http://localhost:8001`. This option serves the built browser interface from FastAPI. Set `ENABLE_AI=true` in root `.env` before the build if you want the larger CPU AI runtime in Docker. Docker/PostGIS deployment was provided as configuration but was not executed in this workspace.

## Troubleshooting

| Problem | Check |
|---|---|
| Vite not recognised | Run dependency installation successfully in the ROOT folder first. |
| Backend unavailable | API must run on **8001** for v2; restart Vite if you changed its proxy. |
| WebSocket upgrade warning | Install `backend/requirements.txt`, which includes `uvicorn[standard]`. |
| Model configured but inference fails | Weights presence is separate from installing the optional AI runtime. Read the API error. |
| No boxes detected | Do not assume every road image contains a detectable pothole; results depend on the model and threshold. |
| Location/camera permission fails | Use localhost on the computer or HTTPS remotely; check browser/Android permissions. |
| Poor GPS | Try outdoors with precise location enabled. Road-level alerts are gated at 60 m accuracy, inference at 50 m. |
| Map/search/route unavailable | Check internet/provider availability. Provider errors are not replaced with fake data. |
| No shelters returned | OSM may have no mapped shelters; hospital-only fallback is labelled. This is not an official shelter database. |
| Expo audit warnings | See docs/TEST-REPORT.md. Do not run `npm audit fix --force`: it proposes an incompatible SDK downgrade. |
| Same report cannot be confirmed twice | Intentional account-level duplicate protection. Use genuinely independent verification. |

## Stop the app

Press **Ctrl+C** in each running terminal. Reports are stored in `backend\roadsense_v2.sqlite`. Back up that file if you need to keep local data. The `.jwt_secret` generated in backend should also be retained privately if you want existing sessions to remain valid after restarting.

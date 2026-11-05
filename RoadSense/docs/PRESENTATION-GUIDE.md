# Present RoadSense while standing still

Open `RoadSense-Presentation.html` in Chrome or Edge. No Python installation, account, backend or physical travel is required. The new Presentation tab in the full browser app provides the same scenario.

## Controls
1. **Play presentation** starts a virtual vehicle on cached real Palakkad road geometry.
2. Choose playback speed (6× default; 12× or 24× for a quicker demonstration).
3. The sample pothole produces an advance warning. **Voice on/off** controls browser speech, where available.
4. **Simulate community confirmation** shows how independent confirmation changes the sample report. It does not write to the database.
5. At the closure checkpoint playback pauses and introduces a clearly labelled sample flood closure.
6. **Show prepared detour** switches to a cached alternative starting exactly at that checkpoint. It avoids the sample closure zone.
7. Vehicle movement resumes on the prepared detour until arrival.
8. **Reset** replays the scenario. **Next scene** skips ahead when your presentation is short.

## Fast examiner walkthrough (no waiting)

Play → Pause → Next scene (warning) → Simulate confirmation → Next scene (closure) → Show prepared detour → Pause → Next scene (arrival) → Reset.

## Explain it honestly

Say: “Because I am presenting indoors, this mode simulates GPS movement and hazard reports. It uses cached real road routes and a prepared detour. The normal app uses actual GPS and online providers. AI inference is a separate real-model test.”

This is not a demonstration of actual camera detection, real disaster reports, live community votes or a live rerouting request. Do not describe those as happening in this simulation. No sample hazards are published to real accounts or the live database.

Basemap tiles need internet and may be unavailable in an embedded file viewer. The route geometry, markers, playback controls, scenario timeline and checkpoint behaviour remain usable without the API. Voice depends on browser support/permissions; if silent in the embedded viewer, download the HTML and open it directly in Chrome/Edge. Keep the simulation label visible during your presentation.

Source data: explicit OSRM public requests produced the cached road shapes in `src/data/presentation.json`. The baseline is approximately 3.18 km; the prepared remaining detour is 5.70 km from the 1.12 km checkpoint. The sample closure is over 723 m from that detour. These are scenario measurements, not current traffic conditions.

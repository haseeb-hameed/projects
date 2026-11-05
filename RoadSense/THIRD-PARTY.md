# Third-party components and attribution

RoadSense's original application code is supplied under AGPL-3.0. This source archive retains the complete source needed to modify the application. Dependency names below are acknowledgements, not an exhaustive software bill of materials; see the two package lockfiles and Python requirements for the dependency graph.

- Ultralytics YOLO: https://github.com/ultralytics/ultralytics — AGPL-3.0 / commercial licensing. Review terms before proprietary or commercial deployment.
- Bundled pothole checkpoint: https://huggingface.co/peterhdd/pothole-detection-yolov8 — repository declares Apache-2.0. Pinned revision, file hash and limitations are documented in models/PROVENANCE.md. Upstream author retains ownership and attribution; this project did not train it.
- Model architecture/training ecosystem: PyTorch, torchvision, Ultralytics. Follow the respective upstream license notices.
- OpenStreetMap contributors: map and road/facility data under the Open Database License; preserve on-map attribution and review derived-database obligations.
- OpenStreetMap standard tile service: https://operations.osmfoundation.org/policies/tiles/ — no bulk/offline prefetch implemented.
- Nominatim public geocoder: https://operations.osmfoundation.org/policies/nominatim/ — explicit submit, caching, upstream request spacing; public service is not for production scale.
- OSRM: https://project-osrm.org/ — road routing; public demo server has no SLA.
- Overpass API: https://wiki.openstreetmap.org/wiki/Overpass_API — OSM queries; no SLA. Hospital lookup and graph planning have labelled fallback modes.
- Leaflet (BSD-2-Clause), React / React Native / Expo (primarily MIT), Vite (MIT), Lucide (ISC), FastAPI (MIT), SQLAlchemy (MIT), PostgreSQL / PostGIS (upstream licenses apply).
- Native Android default map (2.3.1) uses Leaflet 1.9.4 (BSD-2-Clause; mobile/src/leaflet-LICENSE.txt), bundled CSS/JS, react-native-webview and real OpenStreetMap tiles. OSM attribution remains visible. Tile availability and provider usage policy apply; no bulk/offline tile download is implemented. The older Google map view is no longer the default; a Google Maps key is not required by the new view.

Do not claim affiliation with Ather. The interface is original and inspired by clean vehicle-navigation patterns; no Ather logos or proprietary assets are included.

## 2.5 media support

Photo/video picking and playback use Expo image-picker/video under their package licenses. imageio-ffmpeg and its bundled FFmpeg runtime have their own notices; consult the installed wheel/binary licenses before redistributing them. No FFmpeg executable is embedded in the source-update ZIP. Existing Ultralytics model/runtime and project-license obligations remain unchanged.

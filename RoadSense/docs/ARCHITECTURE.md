# Architecture and reasoning

```text
Browser (React + Leaflet)           Android (Expo / React Native)
 camera + geolocation                CameraView + foreground location
 speech + notifications              Expo Speech + local notifications
             \                        /
              HTTP / JWT + WebSockets
                       |
               FastAPI application
       +---------------+----------------+
       |               |                |
 SQLAlchemy       Geospatial /       YOLO inference
 users/reports    graph algorithms   trusted local weights
 unique votes     risk scoring       RAM image decoding
       |               |                |
 SQLite OR        external map       optional auto-report
 PostgreSQL /     providers          spatial/time dedup
 PostGIS
```

## Route costs

- OSRM mode: fetch real driving alternatives, associate reports within a 40 m corridor (100 m for disaster/blocked-road zones), assign risk weights Low=1, Medium=3, High=7. Candidate cost = travel duration in seconds + 90 × risk points. Any high-severity flood/landslide/blocked-road intersection marks the entire candidate blocked, not recommended.
- Graph mode: download eligible OSM roads and respect basic access/motor-vehicle tags, one-way direction and roundabouts. Edge cost = segment length in metres + 200 × risk points on that segment. High-severity closures remove matching edges. Dijkstra uses zero heuristic; A* uses straight-line distance, admissible because costs are non-negative and at least physical length.
- If full graph retrieval fails, build a directed graph from actual OSRM candidate geometries, merging shared coordinate nodes. The planner still genuinely runs Dijkstra/A*, but only over this explicitly limited subgraph. No ETA is manufactured for graph mode.

Risk scoring is a transparent heuristic, not a learned or calibrated accident probability. Segment-level risk penalties can accumulate across adjacent edges near the same report. The selected route is not guaranteed globally safest. Full turn restriction relations, road elevation, flood polygons, weather, lane topology and live traffic are absent.

## Alert geometry

Haversine distance ≤500 m by default. If heading is known, keep reports within a ±65-degree forward cone. If heading is unknown, label them “nearby”, not “ahead”. Reject inaccurate GPS (>60 m). Client cooldown is five minutes per report. This is geographic filtering, not map matching; parallel/overhead roads can still produce irrelevant alerts.

## Verification and freshness

One vote per user/report; users can change their vote. A reporter cannot confirm their own report. Two independent confirms produce confirmed status; owner clearance or two clear votes exceeding confirmation count produce cleared status. Transient reports expire in 24 h; most other reports in seven days. These are prototype policy choices, not verified hazard lifetimes.

## Inference/privacy

Authentication and request-rate gate → bounded upload read → Pillow decode/pixel bound → local model inference lock → whitelisted label mapping → optional report creation. The API does not retain raw images. GPS attached to a detection is the camera capture position. Deduplication combines type, ≤25 m location and one-hour recency, not object tracking. Severity defaults to Medium and is not inferred from confidence.

## Security/deployment boundaries

Passwords are salted scrypt hashes; JWT signing key comes from the environment or a private generated local file. Tokens expire after 24 h. Android stores tokens with SecureStore; browser localStorage tokens require the usual XSS protections and HTTPS. No email verification, token revocation, role-based moderation or password recovery exists. WebSocket authentication is the first frame rather than a token in the URL. In-memory rate limits and broadcasts assume one process. Move these to shared infrastructure before scaling.

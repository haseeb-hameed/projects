# Bundled pothole model — third-party, not trained by this project

- Author/repository: https://huggingface.co/peterhdd/pothole-detection-yolov8
- Pinned revision: `da7747eea7abb4319a0f55961f31809a16c1b10a`
- Original file: `best.pt`
- Local file: `pothole.pt` (22,524,266 bytes)
- SHA256: `af2ac6ce7bfec72e71643659ac946caf80ced84869e526a60135c457abfbb200`
- Repository metadata declares Apache-2.0. Retain upstream attribution and Apache license when redistributing this artifact. The Ultralytics runtime is separately licensed under AGPL-3.0 or a commercial license; this source project is distributed under AGPL-3.0.
- Upstream model card is retained as `UPSTREAM_MODEL_CARD.md`.
- Upstream describes a one-class pothole YOLOv8s detector. The loaded checkpoint names its single class `0`; the backend maps `0` to `Pothole` **only when this bundled checkpoint path is in use**.
- `upstream-validation-preview.jpg` is an already annotated upstream validation montage, not a new independent test dataset. It is retained only as an inference plumbing smoke fixture. It must not be used to claim mAP, accuracy, recall or generalisation.

## What was actually checked

- Checksum and model loading.
- Blank 640×480 RGB image produced no boxes at confidence ≥0.45.
- Upstream annotated preview produced one box at confidence ≈0.461 in this environment. This is not an evaluation; the preview includes prior annotations and multiple images.
- HTTP `/api/detect` returned a mapped `Pothole` detection and valid coordinates for the box.

## What is NOT established

No local-road accuracy, night/rain performance, range accuracy, false-negative rate, frame rate guarantee, or safety qualification is established. No flood, crack, landslide or obstacle AI detector is bundled. These categories can be manually reported. Train and test additional classes before claiming automatic detection of them.

Treat `.pt` files as executable model artifacts. Load only trusted files. Verify the checksum before running this copy. Custom model class mappings must be configured explicitly; do not rename unrelated classes as potholes.

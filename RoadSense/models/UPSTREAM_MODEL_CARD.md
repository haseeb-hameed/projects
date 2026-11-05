---
license: apache-2.0
datasets:
- Ryukijano/Pothole-detection-Yolov8
base_model:
- Ultralytics/YOLOv8
pipeline_tag: object-detection
tags:
- yolov8
- object-detection
---
# YOLOv8 Pothole Detection Model

This model detects potholes in road images using **YOLOv8s** trained on the following dataset: 

[Pothole dataset](https://huggingface.co/datasets/Ryukijano/Pothole-detection-Yolov8/)



## Model Details
- **Architecture:** YOLOv8s (Ultralytics)
- **Task:** Object Detection
- **Classes:** 1 (pothole)
- **Epochs:** 100
- **Hardware:** NVIDIA L40S (Nebius Cloud)
- **Model Size:** 22.5 MB

---

### Sample Prediction
![Prediction](./val_batch1_pred.jpg)

### Training Results
![Results](./results.png)

### Confusion Matrix
![Confusion Matrix](./confusion_matrix.png)

---

## Usage Example (Python)

```python
from ultralytics import YOLO

model = YOLO("https://huggingface.co/peterhdd/pothole-detection-yolov8/resolve/main/best.pt")
results = model("your_image.jpg")
results.show()
```


This model is part of a complete end-to-end pothole detection system including training, GPU inference, and a mobile application.

The repository can be found here:

https://github.com/PeterHdd/pothole-detection-yolo
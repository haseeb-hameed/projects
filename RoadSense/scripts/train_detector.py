"""Train / evaluate on a user-supplied, licensed YOLO dataset. No fabricated metrics."""
import argparse,json,pathlib
p=argparse.ArgumentParser();p.add_argument('--data',required=True,help='YOLO dataset YAML with separated train/val/test');p.add_argument('--model',default='yolov8n.pt');p.add_argument('--epochs',type=int,default=50);p.add_argument('--device',default='cpu');p.add_argument('--evaluate-only',action='store_true');a=p.parse_args()
from ultralytics import YOLO
m=YOLO(a.model)
if not a.evaluate_only:m.train(data=a.data,epochs=a.epochs,imgsz=640,device=a.device,seed=42,project='experiments',name='hazard-detector')
metrics=m.val(data=a.data,split='test',device=a.device)
out={'map50':float(metrics.box.map50),'map50_95':float(metrics.box.map),'classes':m.names,'note':'Evaluate only on held-out images from roads/videos not in training.'}
pathlib.Path('experiments').mkdir(exist_ok=True);pathlib.Path('experiments/evaluation.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))

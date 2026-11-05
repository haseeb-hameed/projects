import sys,pathlib,io
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'backend'))
from PIL import Image
import main
print('Model:',main.MODEL_PATH)
assert main.inference(Image.new('RGB',(640,480)))==[]
preview=pathlib.Path(__file__).resolve().parents[1]/'models/upstream-validation-preview.jpg'
if preview.exists():
 detections=main.inference(Image.open(preview).convert('RGB'));print('Annotated upstream preview smoke:',detections)
 print('This is an annotated upstream montage, NOT a held-out evaluation or an accuracy measurement.')
print('Blank-image negative smoke passed. No road-safety accuracy claim is made.')

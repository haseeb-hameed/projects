import io,subprocess
import pytest
from PIL import Image
from sqlalchemy import select,func
from test_backend import client,account,reset
import main,models,media_routes

@pytest.fixture(autouse=True)
def private_store(tmp_path,monkeypatch):
 monkeypatch.setattr(media_routes,'MEDIA_ROOT',tmp_path/'private_media')

def photo():
 out=io.BytesIO();Image.new('RGB',(120,80),'gray').save(out,format='JPEG');return out.getvalue()
def upload(h,raw=None,name='photo.jpg',mime='image/jpeg'):
 return client.post('/api/media/upload',headers=h,files={'file':(name,raw if raw is not None else photo(),mime)})
def body(id,**extra):return {'type':'Pothole','location':'Verified test road','severity':'Medium','lat':10.78,'lon':76.65,'media_ids':[id],'location_confirmed':True}|extra

def test_upload_auth_and_private_ownership():
 assert upload({}).status_code==401
 a=account();b=account(2);r=upload(a);assert r.status_code==200,r.text;id=r.json()['id']
 assert client.get('/api/media/'+id).status_code==401
 assert client.get('/api/media/'+id,headers=b).status_code==404
 assert client.get('/api/media/'+id,headers=a).status_code==200
 assert client.get('/api/media/../../main.py',headers=a).status_code==404
 assert client.delete('/api/media/'+id,headers=b).status_code==404

def test_reject_bad_media_and_size():
 a=account()
 assert upload(a,b'fake','a.exe','application/octet-stream').status_code==415
 assert upload(a,b'fake').status_code==422
 assert upload(a,b'x'*(5*1024*1024+1)).status_code==413
 assert upload(a,b'bad-video','a.mp4','video/mp4').status_code==422
 assert upload(a,b'x'*(21*1024*1024+1),'a.mp4','video/mp4').status_code==413

def test_reviewed_report_atomic_location_and_attachment_permissions():
 a=account();b=account(2);id=upload(a).json()['id']
 assert client.post('/api/media/reports',headers=a,json=body(id,location_confirmed=False)).status_code==422
 assert client.post('/api/media/reports',headers=b,json=body(id)).status_code==404
 assert client.get('/api/hazards').json()==[]
 r=client.post('/api/media/reports',headers=a,json=body(id));assert r.status_code==200,r.text
 h=client.get('/api/hazards').json()[0];assert h['source']=='media';assert h['attachments'][0]['id']==id
 assert client.get('/api/media/'+id,headers=b).status_code==200
 assert client.post('/api/media/reports',headers=a,json=body(id)).status_code==409
 assert len(client.get('/api/hazards').json())==1
 assert client.delete('/api/media/'+id,headers=a).status_code==200
 assert client.get('/api/hazards').json()[0]['attachments']==[]

def test_duplicate_or_missing_attachment_cannot_create_partial_report():
 a=account();id=upload(a).json()['id']
 assert client.post('/api/media/reports',headers=a,json=body(id,media_ids=[id,id])).status_code==422
 assert client.post('/api/media/reports',headers=a,json=body(id,media_ids=[id,'0'*32])).status_code==404
 assert client.get('/api/hazards').json()==[]

def test_image_ai_readonly_and_no_auto_location(monkeypatch):
 a=account();id=upload(a).json()['id'];calls=[]
 def infer(im,conf):
  calls.append((im.size,conf));return [{'type':'Pothole','confidence':.71,'box':[10,10,70,60]}]
 monkeypatch.setattr(main,'inference',infer)
 r=client.post('/api/media/'+id+'/analyse',headers=a);assert r.status_code==200,r.text
 d=r.json();assert d['saved'] is False;assert d['frames'][0]['preview'].startswith('data:image/jpeg;base64,');assert d['frames'][0]['detections'][0]['type']=='Pothole';assert calls==[((120,80),.35)]
 assert client.get('/api/hazards').json()==[]
 assert client.post('/api/media/'+id+'/analyse',headers=account(2)).status_code==404

def make_video(path,seconds):
 subprocess.run([media_routes.ffmpeg(),'-nostdin','-hide_banner','-loglevel','error','-f','lavfi','-i','color=c=gray:s=160x120:r=5','-t',str(seconds),'-c:v','libx264','-pix_fmt','yuv420p',str(path)],check=True,timeout=30)
 return path.read_bytes()

def test_real_video_decode_sampling_and_readonly_ai(tmp_path,monkeypatch):
 a=account();raw=make_video(tmp_path/'clip.mp4',9)
 r=upload(a,raw,'clip.mp4','video/mp4');assert r.status_code==200,r.text;id=r.json()['id'];assert r.json()['duration']<=10
 monkeypatch.setattr(main,'inference',lambda im,c:[{'type':'Pothole','confidence':.6,'box':[1,1,20,20]}])
 r=client.post('/api/media/'+id+'/analyse',headers=a);assert r.status_code==200,r.text
 d=r.json();assert 1<=len(d['frames'])<=8;assert d['frames'][0]['image_size']==[160,120];assert d['frames'][0]['detections'];assert client.get('/api/hazards').json()==[]
 response=client.get('/api/media/'+id,headers=a|{'Range':'bytes=0-31'});assert response.status_code in (200,206)

def test_video_duration_limit(tmp_path):
 a=account();raw=make_video(tmp_path/'long.mp4',31)
 assert upload(a,raw,'long.mp4','video/mp4').status_code==422

def test_delete_draft_and_missing_model_check():
 a=account();id=upload(a).json()['id'];assert client.post('/api/media/'+id+'/analyse',headers=a).status_code==503
 assert client.post('/api/vision/check',headers=a).status_code==503
 assert client.delete('/api/media/'+id,headers=a).status_code==200
 assert client.get('/api/media/'+id,headers=a).status_code==404

def test_vision_check_is_readonly(monkeypatch):
 a=account();monkeypatch.setattr(main,'inference',lambda im,c:[])
 r=client.post('/api/vision/check',headers=a);assert r.status_code==200,r.text;assert r.json()['ok']
 assert client.get('/api/hazards').json()==[]

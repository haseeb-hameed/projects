import io
from PIL import Image
from test_backend import client,account,reset
from test_media import private_store,upload,body
import models,media_routes

def test_photo_metadata_removed_and_my_evidence_is_owner_only():
 a=account();b=account(2);im=Image.new('RGB',(100,80));exif=Image.Exif();exif[270]='Private metadata';out=io.BytesIO();im.save(out,format='JPEG',exif=exif)
 r=upload(a,out.getvalue());assert r.status_code==200,r.text;id=r.json()['id']
 with models.Session() as s:
  item=s.get(models.MediaAttachment,id)
  with Image.open(media_routes.disk_path(item)) as stored:assert len(stored.getexif())==0
 assert client.get('/api/media/mine',headers=b).json()==[]
 mine=client.get('/api/media/mine',headers=a).json();assert mine[0]['id']==id
 assert client.get('/api/media/mine').status_code==401

def test_file_count_quota_and_own_deletion():
 a=account()
 with models.Session() as s:
  u=s.query(models.User).first()
  for i in range(100):s.add(models.MediaAttachment(id=f'{i:032x}',user_id=u.id,kind='image',mime='image/jpeg',size=1))
  s.commit()
 assert upload(a).status_code==413
 assert len(client.get('/api/media/mine',headers=a).json())==100
 assert client.delete('/api/media/'+f'{0:032x}',headers=a).status_code==200
 assert upload(a).status_code==200

def test_cleared_report_evidence_remains_owner_accessible_but_not_other_users():
 a=account();b=account(2);id=upload(a).json()['id'];r=client.post('/api/media/reports',headers=a,json=body(id));assert r.status_code==200,r.text
 assert client.get('/api/media/'+id,headers=b).status_code==200
 assert client.post('/api/hazards/'+str(r.json()['id'])+'/clear',headers=a).status_code==200
 assert client.get('/api/media/'+id,headers=b).status_code==404
 assert client.get('/api/media/'+id,headers=a).status_code==200
 assert client.get('/api/media/mine',headers=a).json()[0]['id']==id
 assert client.delete('/api/media/'+id,headers=a).status_code==200

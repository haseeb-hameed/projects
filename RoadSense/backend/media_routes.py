"""Private evidence uploads, read-only sampled AI analysis and reviewed reports.
Never derive a recorded file's road location from the uploader's current GPS.
"""
import asyncio,base64,io,json,math,os,re,secrets,subprocess,tempfile,time
from pathlib import Path
from PIL import Image,ImageOps,UnidentifiedImageError
from fastapi import Depends,File,UploadFile,HTTPException
from fastapi.responses import FileResponse,JSONResponse
from pydantic import Field
from sqlalchemy import select,func
from models import BASE,Session,MediaAttachment,Hazard,Zone,now

MEDIA_ROOT=Path(os.getenv('MEDIA_ROOT',str(BASE/'private_media')))
MAX_BYTES=20*1024*1024

def metadata(a):
 return {'id':a.id,'kind':a.kind,'mime':a.mime,'size':a.size,'duration':a.duration,'url':'/api/media/'+a.id,'hazard_id':a.hazard_id,'created':a.created}
def disk_path(a):return MEDIA_ROOT/(a.id+('.jpg' if a.kind=='image' else '.mp4'))
def owned(s,id,u):
 if not re.fullmatch('[a-f0-9]{32}',id):raise HTTPException(404,'Media not found')
 a=s.get(MediaAttachment,id)
 if not a or a.user_id!=u.id:raise HTTPException(404,'Media not found')
 return a

def ffmpeg():
 try:
  import imageio_ffmpeg
  return imageio_ffmpeg.get_ffmpeg_exe()
 except (ImportError,RuntimeError):raise HTTPException(503,'Install updated backend/requirements.txt (imageio-ffmpeg) for video support')
def video_duration(path):
 try:p=subprocess.run([ffmpeg(),'-hide_banner','-protocol_whitelist','file,pipe','-i',str(path)],capture_output=True,timeout=15)
 except subprocess.TimeoutExpired:raise HTTPException(422,'Video inspection timed out')
 text=p.stderr.decode('utf8',errors='replace');match=re.search(r'Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)',text)
 if not match or not re.search(r'Video:',text):raise HTTPException(422,'Use a readable MP4/MOV video with a video track')
 h,m,s=map(float,match.groups());duration=h*3600+m*60+s
 if not math.isfinite(duration) or not 0<duration<=30.1:raise HTTPException(422,'Video must be 30 seconds or shorter; trim it before uploading')
 return duration

def validate_upload(raw,mime):
 if mime in ('image/jpeg','image/png'):
  if len(raw)>5*1024*1024:raise HTTPException(413,'Photo exceeds 5 MB')
  try:
   im=Image.open(io.BytesIO(raw))
   if im.format not in ('JPEG','PNG') or im.width*im.height>16_000_000:raise HTTPException(422,'Use a JPEG/PNG photo at most 16 megapixels')
   im=ImageOps.exif_transpose(im).convert('RGB');im.thumbnail((1920,1920));out=io.BytesIO();im.save(out,format='JPEG',quality=88)
   return out.getvalue(),'image','image/jpeg',None
  except (UnidentifiedImageError,OSError,Image.DecompressionBombError):raise HTTPException(422,'Invalid JPEG/PNG photo')
 if mime not in ('video/mp4','video/quicktime'):raise HTTPException(415,'Choose JPEG/PNG or MP4/MOV, not an arbitrary file')
 if len(raw)<12 or raw[4:8]!=b'ftyp':raise HTTPException(422,'Not a valid MP4/MOV container')
 MEDIA_ROOT.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(dir=MEDIA_ROOT) as temp:
  p=Path(temp)/'inspect.mp4';p.write_bytes(raw);duration=video_duration(p)
 return raw,'video',mime,duration

def analyse_file(a,infer):
 samples=[]
 if a.kind=='image':
  with Image.open(disk_path(a)) as im:samples.append((0,im.convert('RGB').copy()))
 else:
  with tempfile.TemporaryDirectory(dir=MEDIA_ROOT) as temp:
   try:
    proc=subprocess.run([ffmpeg(),'-nostdin','-hide_banner','-loglevel','error','-protocol_whitelist','file,pipe','-i',str(disk_path(a)),'-t','30','-vf',"fps=1/4,scale='min(960,iw)':'min(960,ih)':force_original_aspect_ratio=decrease",'-frames:v','8','-threads','1',str(Path(temp)/'frame_%02d.jpg')],capture_output=True,timeout=45)
   except subprocess.TimeoutExpired:raise HTTPException(422,'Video decoding timed out; choose a shorter clip')
   if proc.returncode:raise HTTPException(422,'Video cannot be decoded; export a standard H.264 MP4')
   for i,p in enumerate(sorted(Path(temp).glob('frame_*.jpg'))):
    with Image.open(p) as im:samples.append((min(a.duration or 30,2+4*i),im.convert('RGB').copy()))
  if not samples:raise HTTPException(422,'No video frames decoded')
 frames=[]
 for i,(seconds,im) in enumerate(samples):
  im.thumbnail((960,960));detections=infer(im,.35);out=io.BytesIO();im.save(out,format='JPEG',quality=72)
  frames.append({'frame_id':i,'seconds':seconds,'image_size':list(im.size),'detections':detections,'preview':'data:image/jpeg;base64,'+base64.b64encode(out.getvalue()).decode()})
 return {'media_id':a.id,'frames':frames,'sampled_frames':len(frames),'threshold':.35,'saved':False,'note':'Read-only actual model results. Video sampling can miss hazards between frames. Confidence is not severity. Location is unknown until you confirm it.'}

class MediaBodyLimit:
 def __init__(self,app):self.app=app
 async def __call__(self,scope,receive,send):
  if scope['type']!='http' or scope.get('path')!='/api/media/upload':return await self.app(scope,receive,send)
  headers=dict(scope.get('headers',[]));length=headers.get(b'content-length',b'0')
  if length.isdigit() and int(length)>MAX_BYTES+1024*1024:return await JSONResponse({'detail':'Upload exceeds 20 MB media limit'},status_code=413)(scope,receive,send)
  total=0
  async def bounded():
   nonlocal total
   message=await receive();total+=len(message.get('body',b''))
   if total>MAX_BYTES+1024*1024:raise HTTPException(413,'Upload exceeds 20 MB media limit')
   return message
  await self.app(scope,bounded,send)

def install_media_routes(app,current,infer,Report,broadcast,throttle,frame_slots):
 app.add_middleware(MediaBodyLimit)
 uploads=asyncio.Semaphore(2);storage_lock=asyncio.Lock()
 class ReviewedReport(Report):
  media_ids:list[str]=Field(min_length=1,max_length=3)
  location_confirmed:bool=False

 @app.post('/api/media/upload')
 async def upload(file:UploadFile=File(...),u=Depends(current)):
  throttle(('media-upload',u.id),20)
  try:await asyncio.wait_for(uploads.acquire(),.1)
  except asyncio.TimeoutError:raise HTTPException(429,'Uploads busy; retry shortly')
  try:
   raw=await file.read(MAX_BYTES+1)
   if not raw or len(raw)>MAX_BYTES:raise HTTPException(413,'Choose a nonempty file no larger than 20 MB')
   content,kind,mime,duration=await asyncio.to_thread(validate_upload,raw,file.content_type)
   async with storage_lock:
    with Session() as s:
     # Remove only this owner's expired, unattached drafts; published evidence is retained.
     for old in s.scalars(select(MediaAttachment).where(MediaAttachment.user_id==u.id,MediaAttachment.hazard_id==None,MediaAttachment.created<now()-86400)).all():
      disk_path(old).unlink(missing_ok=True);s.delete(old)
     s.flush()
     used=s.scalar(select(func.coalesce(func.sum(MediaAttachment.size),0)).where(MediaAttachment.user_id==u.id))
     total=s.scalar(select(func.coalesce(func.sum(MediaAttachment.size),0)))
     count=s.scalar(select(func.count()).select_from(MediaAttachment).where(MediaAttachment.user_id==u.id))
     total_count=s.scalar(select(func.count()).select_from(MediaAttachment))
     if count>=100 or total_count>=10000 or used+len(content)>100*1024*1024 or total+len(content)>1024*1024*1024:raise HTTPException(413,'Evidence storage quota reached; delete unused media')
     a=MediaAttachment(id=secrets.token_hex(16),user_id=u.id,kind=kind,mime=mime,size=len(content),duration=duration)
     MEDIA_ROOT.mkdir(parents=True,exist_ok=True)
     try:
      disk_path(a).write_bytes(content);s.add(a);s.commit()
     except Exception:
      disk_path(a).unlink(missing_ok=True);raise
     return metadata(a)
  finally:uploads.release()

 @app.get('/api/media/mine')
 def my_media(u=Depends(current)):
  with Session() as s:return [metadata(a) for a in s.scalars(select(MediaAttachment).where(MediaAttachment.user_id==u.id).order_by(MediaAttachment.created.desc()).limit(100))]

 @app.get('/api/media/{id}')
 def fetch_media(id:str,u=Depends(current)):
  if not re.fullmatch('[a-f0-9]{32}',id):raise HTTPException(404,'Media not found')
  with Session() as s:
   a=s.get(MediaAttachment,id)
   if not a:raise HTTPException(404,'Media not found')
   if a.user_id!=u.id:
    h=s.get(Hazard,a.hazard_id) if a.hazard_id else None
    if not h or h.status=='cleared' or h.expires<now():raise HTTPException(404,'Media not found')
   path=disk_path(a)
   if not path.is_file():raise HTTPException(404,'Evidence file unavailable')
   return FileResponse(path,media_type=a.mime,headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'})

 @app.delete('/api/media/{id}')
 async def delete_media(id:str,u=Depends(current)):
  throttle(('media-delete',u.id),30)
  async with storage_lock:
   with Session() as s:
    a=owned(s,id,u);disk_path(a).unlink(missing_ok=True);s.delete(a);s.commit()
  return {'deleted':True,'id':id}

 @app.post('/api/media/{id}/analyse')
 async def analyse(id:str,u=Depends(current)):
  throttle(('media-analysis',u.id),10)
  with Session() as s:a=owned(s,id,u)
  if not disk_path(a).is_file():raise HTTPException(404,'Evidence file unavailable')
  try:await asyncio.wait_for(frame_slots.acquire(),.1)
  except asyncio.TimeoutError:raise HTTPException(429,'AI busy; wait and retry')
  started=time.monotonic()
  try:result=await asyncio.to_thread(analyse_file,a,infer)
  except FileNotFoundError:raise HTTPException(404,'Evidence was deleted; upload it again')
  finally:frame_slots.release()
  result['elapsed_ms']=round((time.monotonic()-started)*1000)
  # Do not persist previews or automatically create reports.
  return result

 @app.post('/api/media/reports')
 async def reviewed_report(data:ReviewedReport,u=Depends(current)):
  throttle(('media-report',u.id),20)
  if not data.location_confirmed:raise HTTPException(422,'Explicitly confirm the real capture location; current phone GPS may not match recorded media')
  if len(set(data.media_ids))!=len(data.media_ids):raise HTTPException(422,'Choose distinct evidence attachments')
  async with storage_lock:
   with Session() as s:
    rows=[owned(s,id,u) for id in data.media_ids]
    if any(a.hazard_id is not None for a in rows):raise HTTPException(409,'Evidence is already attached to a report')
    if any(not disk_path(a).is_file() for a in rows):raise HTTPException(404,'Evidence file unavailable; upload it again')
    # Atomic report + evidence association. Human-reviewed, not automatic camera inference.
    values=data.model_dump(exclude={'media_ids','location_confirmed'})
    h=Hazard(user_id=u.id,**values,source='media',confidence=None,expires=now()+(86400 if data.type in ('Waterlogging','Flood','Obstacle','Blocked road') else 7*86400));s.add(h);s.flush()
    if data.type in ('Flood','Landslide','Blocked road') and data.severity=='High':s.add(Zone(hazard_id=h.id,radius=100))
    for a in rows:a.hazard_id=h.id
    s.commit();out={k:getattr(h,k) for k in ['id','type','location','severity','lat','lon','source','created','user_id']};out['attachments']=[metadata(a) for a in rows]
  await broadcast({'event':'hazard_created','hazard':out});return out

 @app.post('/api/vision/check')
 async def check(u=Depends(current)):
  throttle(('vision-check',u.id),4)
  try:await asyncio.wait_for(frame_slots.acquire(),.1)
  except asyncio.TimeoutError:raise HTTPException(429,'AI busy; retry after the current request finishes')
  started=time.monotonic()
  try:await asyncio.to_thread(infer,Image.new('RGB',(320,320)),.35)
  finally:frame_slots.release()
  return {'ok':True,'elapsed_ms':round((time.monotonic()-started)*1000),'note':'Backend blank-image inference passed; this does not verify phone camera upload or road accuracy.'}

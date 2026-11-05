import os,time,json,secrets,hashlib,hmac,asyncio,math,io,threading
from pathlib import Path
from contextlib import asynccontextmanager
from collections import defaultdict,deque
from typing import Literal
import jwt
from fastapi import FastAPI,HTTPException,Depends,UploadFile,File,Form,WebSocket,WebSocketDisconnect,Query,Request
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel,Field,field_validator
from sqlalchemy import select,func,text
from sqlalchemy.exc import IntegrityError
from PIL import Image,UnidentifiedImageError
from models import Session,User,Hazard,Vote,Zone,MediaAttachment,now,BASE,URL
from geo import distance,bearing
import providers
from mobile_tracking import CameraSessions,SessionError

secret_path=BASE/'.jwt_secret'
SECRET=os.getenv('JWT_SECRET')
if not SECRET:
 if not secret_path.exists():secret_path.write_text(secrets.token_hex(32));secret_path.chmod(0o600)
 SECRET=secret_path.read_text().strip()
@asynccontextmanager
async def lifespan(app):
 yield
app=FastAPI(title='RoadSense',version='2.5.0',lifespan=lifespan,description='GPS reports, real routing, community verification and optional local YOLO inference. No synthetic hazard or route fallback.')
origins=[x.strip() for x in os.getenv('CORS_ORIGINS','http://localhost:5173,http://localhost:5174').split(',') if x.strip()]
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_methods=['GET','POST','DELETE'],allow_headers=['Authorization','Content-Type'])
security=HTTPBearer(auto_error=False);connections=set();limits=defaultdict(deque)
KINDS=Literal['Pothole','Crack','Waterlogging','Obstacle','Road work','Blocked road','Flood','Landslide']

def throttle(key,n=30,seconds=60):
 q=limits[key];t=time.monotonic()
 while q and t-q[0]>seconds:q.popleft()
 if len(q)>=n:raise HTTPException(429,'Too many requests. Please wait a minute.')
 q.append(t)
def password_hash(password):
 salt=secrets.token_hex(16);digest=hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex();return salt+':'+digest
def password_ok(password,stored):
 salt,digest=stored.split(':');test=hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex();return hmac.compare_digest(test,digest)
def token_for(user):return jwt.encode({'sub':str(user.id),'exp':int(time.time())+86400,'iat':int(time.time()),'iss':'roadsense'},SECRET,algorithm='HS256')
def read_token(token):
 try:
  data=jwt.decode(token,SECRET,algorithms=['HS256'],issuer='roadsense');uid=int(data['sub'])
 except (jwt.PyJWTError,ValueError,KeyError):raise HTTPException(401,'Session expired. Sign in again.')
 with Session() as s:
  u=s.get(User,uid)
  if not u:raise HTTPException(401,'Account not found')
  return u
def current(auth:HTTPAuthorizationCredentials=Depends(security)):
 if not auth:raise HTTPException(401,'Sign in to continue')
 return read_token(auth.credentials)
def user_json(u):return {'id':u.id,'name':u.name,'email':u.email}
class Register(BaseModel):
 name:str=Field(min_length=2,max_length=60);email:str=Field(min_length=5,max_length=160);password:str=Field(min_length=8,max_length=128)
 @field_validator('name','email')
 @classmethod
 def trim(cls,v):return v.strip()
 @field_validator('email')
 @classmethod
 def email_shape(cls,v):
  if '@' not in v or '.' not in v.rsplit('@',1)[-1]:raise ValueError('Enter a valid email')
  return v.lower()
class Login(BaseModel):
 email:str=Field(min_length=3,max_length=160);password:str=Field(min_length=1,max_length=128)
@app.post('/api/auth/register')
def register(data:Register,request:Request):
 throttle(('auth',request.client.host),10)
 with Session() as s:
  u=User(name=data.name,email=data.email,password=password_hash(data.password));s.add(u)
  try:s.commit()
  except IntegrityError:s.rollback();raise HTTPException(409,'An account already exists with this email')
  return {'token':token_for(u),'user':user_json(u)}
@app.post('/api/auth/login')
def login(data:Login,request:Request):
 throttle(('auth',request.client.host),10)
 with Session() as s:
  u=s.scalar(select(User).where(User.email==data.email.strip().lower()))
  if not u or not password_ok(data.password,u.password):raise HTTPException(401,'Email or password is incorrect')
  return {'token':token_for(u),'user':user_json(u)}
@app.get('/api/auth/me')
def me(u=Depends(current)):return user_json(u)

def serialize(h,s):
 votes=s.execute(select(Vote.action,func.count()).where(Vote.hazard_id==h.id).group_by(Vote.action)).all();counts=dict(votes)
 return {k:getattr(h,k) for k in ['id','type','location','severity','lat','lon','source','confidence','status','created','updated','expires','user_id']}|{'confirmations':counts.get('confirm',0),'clear_votes':counts.get('clear',0),'closure':h.type in ('Flood','Landslide','Blocked road') and h.severity=='High','attachments':[{'id':a.id,'kind':a.kind,'mime':a.mime,'size':a.size,'duration':a.duration,'url':'/api/media/'+a.id} for a in s.scalars(select(MediaAttachment).where(MediaAttachment.hazard_id==h.id))]}
def active_hazards():
 with Session() as s:return [serialize(h,s) for h in s.scalars(select(Hazard).where(Hazard.status!='cleared',Hazard.expires>now()).order_by(Hazard.created.desc()))]
async def broadcast(event):
 for ws in list(connections):
  try:await ws.send_json(event)
  except Exception:connections.discard(ws)
class Report(BaseModel):
 type:KINDS;location:str=Field(min_length=2,max_length=160);severity:Literal['Low','Medium','High']='Medium'
 lat:float=Field(ge=-90,le=90,allow_inf_nan=False);lon:float=Field(ge=-180,le=180,allow_inf_nan=False)
 @field_validator('location')
 @classmethod
 def location_trim(cls,v):
  v=v.strip()
  if len(v)<2:raise ValueError('Enter a road or landmark')
  return v
@app.get('/api/hazards')
def hazards(lat:float|None=Query(None,ge=-90,le=90),lon:float|None=Query(None,ge=-180,le=180),radius:float=Query(10000,ge=50,le=100000)):
 if URL.startswith('postgresql') and lat is not None and lon is not None:
  with Session() as s:
   ids=s.execute(text("SELECT id FROM hazards WHERE status != 'cleared' AND expires > :now AND ST_DWithin(ST_SetSRID(ST_MakePoint(lon,lat),4326)::geography, ST_SetSRID(ST_MakePoint(:lon,:lat),4326)::geography, :radius)"),{'lat':lat,'lon':lon,'radius':radius,'now':now()}).scalars().all()
   return [serialize(s.get(Hazard,id),s)|{'distance':round(distance((lat,lon),(s.get(Hazard,id).lat,s.get(Hazard,id).lon)))} for id in ids]
 rows=active_hazards()
 if lat is not None and lon is not None:rows=[h|{'distance':round(distance((lat,lon),(h['lat'],h['lon'])))} for h in rows if distance((lat,lon),(h['lat'],h['lon']))<=radius]
 return rows
async def save_report(data,u,source='manual',confidence=None,captured_at=None):
 with Session() as s:
  # Spatial/temporal deduplication for automatic reports only; no raw image retained.
  if source=='camera':
   recent=s.scalars(select(Hazard).where(Hazard.type==data.type,Hazard.status!='cleared',Hazard.created>now()-3600)).all()
   for h in recent:
    if distance((data.lat,data.lon),(h.lat,h.lon))<25:return serialize(h,s)|{'deduplicated':True}
  h=Hazard(user_id=u.id,**data.model_dump(),source=source,confidence=confidence,created=captured_at if captured_at is not None else now(),expires=now()+(24*3600 if data.type in ('Waterlogging','Flood','Obstacle','Blocked road') else 7*86400));s.add(h);s.flush()
  if data.type in ('Flood','Landslide','Blocked road') and data.severity=='High':s.add(Zone(hazard_id=h.id,radius=100))
  s.commit();out=serialize(h,s)
 await broadcast({'event':'hazard_created','hazard':out});return out
@app.post('/api/hazards')
async def report(data:Report,u=Depends(current)):
 throttle(('report',u.id),20);return await save_report(data,u)
@app.post('/api/hazards/{id}/{action}')
async def vote(id:int,action:Literal['confirm','clear'],u=Depends(current)):
 throttle(('vote',u.id),60)
 with Session() as s:
  h=s.get(Hazard,id)
  if not h or h.status=='cleared' or h.expires<now():raise HTTPException(404,'Active report not found')
  if h.user_id==u.id and action=='confirm':raise HTTPException(409,'You cannot confirm your own report')
  v=s.scalar(select(Vote).where(Vote.user_id==u.id,Vote.hazard_id==id))
  if v and v.action==action:raise HTTPException(409,'You already submitted this verification')
  if v:v.action=action
  else:s.add(Vote(user_id=u.id,hazard_id=id,action=action))
  try:s.flush()
  except IntegrityError:s.rollback();raise HTTPException(409,'Verification already recorded')
  confirms=s.scalar(select(func.count()).select_from(Vote).where(Vote.hazard_id==id,Vote.action=='confirm'));clears=s.scalar(select(func.count()).select_from(Vote).where(Vote.hazard_id==id,Vote.action=='clear'))
  if (u.id==h.user_id and action=='clear') or (clears>=2 and clears>confirms):h.status='cleared'
  elif confirms>=2:h.status='confirmed'
  else:h.status='reported'
  h.updated=now();s.commit();out=serialize(h,s)
 await broadcast({'event':'hazard_updated','hazard':out});return out
@app.get('/api/zones')
def zones():return [h|{'radius':100} for h in active_hazards() if h['closure']]
@app.get('/api/search')
async def search(q:str=Query(min_length=3,max_length=160),request:Request=None):
 throttle(('search',request.client.host),10);return await providers.search(q)
class RouteRequest(BaseModel):
 origin_lat:float=Field(ge=-90,le=90,allow_inf_nan=False);origin_lon:float=Field(ge=-180,le=180,allow_inf_nan=False)
 dest_lat:float=Field(ge=-90,le=90,allow_inf_nan=False);dest_lon:float=Field(ge=-180,le=180,allow_inf_nan=False)
 algorithm:Literal['alternatives','astar','dijkstra']='alternatives'
@app.post('/api/routes')
async def routes(data:RouteRequest,request:Request):
 throttle(('route',request.client.host),12)
 origin=(data.origin_lat,data.origin_lon);dest=(data.dest_lat,data.dest_lon)
 if distance(origin,dest)<20:raise HTTPException(422,'Choose a destination at least 20 m from the start')
 if distance(origin,dest)>200000:raise HTTPException(422,'Prototype supports trips up to 200 km')
 hs=active_hazards()
 if data.algorithm=='alternatives':return await providers.osrm_routes(origin,dest,hs)
 return await providers.graph_route(origin,dest,hs,data.algorithm)
@app.get('/api/facilities')
async def facilities(lat:float=Query(ge=-90,le=90),lon:float=Query(ge=-180,le=180),request:Request=None):
 throttle(('facility',request.client.host),6);return await providers.facilities(lat,lon)
class Position(BaseModel):
 lat:float=Field(ge=-90,le=90,allow_inf_nan=False);lon:float=Field(ge=-180,le=180,allow_inf_nan=False)
 heading:float|None=Field(None,ge=0,le=360,allow_inf_nan=False);accuracy:float=Field(default=20,ge=0,le=10000)
 radius:float=Field(default=500,ge=50,le=1000)
@app.post('/api/alerts')
def alerts(p:Position,u=Depends(current)):
 if p.accuracy>60:return {'alerts':[],'warning':'GPS accuracy is too low for road-level alerts'}
 out=[]
 for h in active_hazards():
  d=distance((p.lat,p.lon),(h['lat'],h['lon']))
  if d>p.radius:continue
  angle=bearing((p.lat,p.lon),(h['lat'],h['lon']));delta=None if p.heading is None else abs((angle-p.heading+180)%360-180)
  if delta is not None and delta>65:continue
  out.append(h|{'distance':round(d),'bearing':round(angle),'message':f"{h['type']} reported {max(10,round(d/10)*10)} metres {'ahead' if p.heading is not None else 'nearby'}. Please proceed carefully."})
 out.sort(key=lambda h:h['distance']);return {'alerts':out,'warning':'Geometric proximity alerts can include parallel roads; check road context.'}

# A local trained model is optional; missing weights produce an explicit 503, never fabricated boxes.
BUNDLED_MODEL=BASE.parent/'models'/'pothole.pt'
MODEL_PATH=os.getenv('YOLO_MODEL_PATH',str(BUNDLED_MODEL) if BUNDLED_MODEL.is_file() else '');MODEL=None;model_lock=threading.Lock()
CLASS_MAP={'pothole':'Pothole','potholes':'Pothole','crack':'Crack','waterlogging':'Waterlogging','obstacle':'Obstacle','fallen object':'Obstacle','flood':'Flood','landslide':'Landslide','blocked road':'Blocked road'}
if MODEL_PATH and Path(MODEL_PATH).resolve()==BUNDLED_MODEL.resolve():CLASS_MAP['0']='Pothole'
try:
 CLASS_MAP.update(json.loads(os.getenv('YOLO_CLASS_MAP','{}')))
except json.JSONDecodeError:raise RuntimeError('YOLO_CLASS_MAP must be valid JSON')
def inference(image,confidence=.45):
 global MODEL
 if not MODEL_PATH or not Path(MODEL_PATH).is_file():raise HTTPException(503,'No trained hazard model configured. Set YOLO_MODEL_PATH to trusted local .pt weights. Detection is unavailable.')
 with model_lock:
  try:
   if MODEL is None:
    from ultralytics import YOLO
    MODEL=YOLO(MODEL_PATH)
   results=MODEL.predict(image,conf=confidence,verbose=False,imgsz=640)
   out=[]
   for result in results:
    for box in result.boxes:
     label=str(result.names[int(box.cls.item())]).lower().strip().replace('_',' ')
     if label not in CLASS_MAP:continue
     out.append({'type':CLASS_MAP[label],'class':label,'confidence':round(float(box.conf.item()),4),'box':[round(float(x),1) for x in box.xyxy[0].tolist()]})
   return out
  except ImportError:raise HTTPException(503,'Install backend/requirements-ai.txt to enable local inference')
  except HTTPException:raise
  except Exception as e:raise HTTPException(503,'Model inference failed. Inspect the trusted model and server configuration.') from e
frame_slots=asyncio.Semaphore(2)
@app.post('/api/vision/frame')
async def preview_frame(request:Request,image:UploadFile=File(...),confidence:float=Form(.35,ge=.1,le=.9),frame_id:int=Form(0,ge=0),source:Literal['video','camera','image']=Form('video')):
 # Read-only analysis: deliberately no GPS parameters and no report writes.
 throttle(('vision',request.client.host),300)
 raw=await image.read(5*1024*1024+1)
 if len(raw)>5*1024*1024:raise HTTPException(413,'Frame exceeds 5 MB')
 try:
  im=Image.open(io.BytesIO(raw))
  if im.width*im.height>16_000_000:raise HTTPException(413,'Frame exceeds 16 megapixels')
  im=im.convert('RGB');im.load()
 except (UnidentifiedImageError,OSError,Image.DecompressionBombError):raise HTTPException(422,'Upload a valid JPEG or PNG frame')
 try:await asyncio.wait_for(frame_slots.acquire(),timeout=.1)
 except asyncio.TimeoutError:raise HTTPException(429,'Detector is busy. Wait briefly and retry.')
 started=time.perf_counter()
 try:detections=await asyncio.to_thread(inference,im,confidence)
 finally:frame_slots.release()
 return {'frame_id':frame_id,'source':source,'detections':detections,'image_size':[im.width,im.height],'inference_ms':round((time.perf_counter()-started)*1000,1),'threshold':confidence,'reports':[],'saved':False,'privacy':'Individual frame processed in memory. No video or report stored.','note':'Confidence is not severity. Pothole model only; no real-time speed guarantee.'}

camera_sessions=CameraSessions()
@app.post('/api/mobile/frame')
async def mobile_frame(
 image:UploadFile=File(...),session_id:str=Form(...,min_length=16,max_length=80,pattern=r'^[A-Za-z0-9_-]+$'),
 sequence:int=Form(...,ge=1),captured_at:float=Form(...),share:bool=Form(True),
 lat:float|None=Form(None,ge=-90,le=90),lon:float|None=Form(None,ge=-180,le=180),
 accuracy:float=Form(10000,ge=0,le=10000),gps_at:float=Form(0),u=Depends(current)):
 throttle(('mobile-frame',u.id),300)
 if not math.isfinite(captured_at) or not math.isfinite(gps_at) or not -5<=now()-captured_at<=60:
  raise HTTPException(422,'Camera timestamp must be recent. Enable automatic date/time on the phone.')
 raw=await image.read(5*1024*1024+1)
 if len(raw)>5*1024*1024:raise HTTPException(413,'Camera frame exceeds 5 MB')
 try:
  im=Image.open(io.BytesIO(raw))
  if im.width*im.height>16_000_000:raise HTTPException(413,'Camera frame exceeds 16 megapixels; resize before upload')
  im=im.convert('RGB');im.load()
 except (UnidentifiedImageError,OSError,Image.DecompressionBombError):raise HTTPException(422,'Camera frame is not a valid image')
 try:session=camera_sessions.begin(u.id,session_id,sequence)
 except SessionError as e:raise HTTPException(409,str(e))
 started=time.perf_counter();reports=[];eligible=[];status='preview_only'
 try:
  try:await asyncio.wait_for(frame_slots.acquire(),timeout=.1)
  except asyncio.TimeoutError:raise HTTPException(429,'Detector busy. Retry with the next frame.')
  try:detections=await asyncio.to_thread(inference,im,.35)
  finally:frame_slots.release()
  eligible=session.observe(detections,(im.width,im.height),captured_at)
  gps_valid=lat is not None and lon is not None and accuracy<=50 and -2<=captured_at-gps_at<=30
  if not session.enabled:status='stopped'
  elif share:
   if not gps_valid:status='gps_unreliable'
   elif not eligible:status='verifying' if session.tracks else 'no_eligible_detection'
   else:
    status='cooldown'
    for d in eligible:
     if not session.enabled:break
     if now()-session.shared.get(d['type'],0)<10:continue
     result=await save_report(Report(type=d['type'],location='Phone rear camera — capture GPS',severity='Medium',lat=lat,lon=lon),u,'camera',d['confidence'],captured_at)
     session.shared[d['type']]=now();reports.append(result)
    if reports:status='deduplicated' if all(r.get('deduplicated') for r in reports) else 'saved'
  return {'session_id':session_id,'sequence':sequence,'captured_at':captured_at,'detections':detections,
   'image_size':[im.width,im.height],'inference_ms':round((time.perf_counter()-started)*1000,1),
   'report_status':status,'reports':reports,'gps_valid':gps_valid,
   'verification_counts':{k:v['count'] for k,v in session.tracks.items()},
   'policy':{'min_confidence':.60,'consecutive_frames':3,'max_frame_gap_seconds':5,'cooldown_seconds':10},
   'note':'Actual backend inference. Capture GPS is not projected object position. Severity is Medium / unassessed.'}
 finally:session.busy=False;session.touched=time.monotonic()

@app.post('/api/mobile/session/{session_id}/stop')
async def stop_mobile_session(session_id:str,u=Depends(current)):
 throttle(('mobile-stop',u.id),30)
 if not 16<=len(session_id)<=80 or any(not(c.isascii() and (c.isalnum() or c in '_-')) for c in session_id):raise HTTPException(422,'Invalid camera session identifier')
 try:camera_sessions.end(u.id,session_id)
 except SessionError as e:raise HTTPException(503,str(e))
 return {'session_id':session_id,'stopped':True,'note':'Already committed reports are not deleted.'}

@app.post('/api/detect')
async def detect(image:UploadFile=File(...),lat:float=Form(...,ge=-90,le=90),lon:float=Form(...,ge=-180,le=180),accuracy:float=Form(...,ge=0,le=10000),save:bool=Form(False),u=Depends(current)):
 throttle(('detect',u.id),20)
 if accuracy>50:raise HTTPException(422,'GPS accuracy must be 50 m or better for geotagged inference')
 raw=await image.read(5*1024*1024+1)
 if len(raw)>5*1024*1024:raise HTTPException(413,'Image exceeds 5 MB')
 try:
  im=Image.open(io.BytesIO(raw))
  if im.width*im.height>16_000_000:raise HTTPException(413,'Image exceeds 16 megapixels')
  im=im.convert('RGB');im.load()
 except (UnidentifiedImageError,OSError,Image.DecompressionBombError):raise HTTPException(422,'Upload a valid JPEG or PNG image')
 detections=await asyncio.to_thread(inference,im);reports=[]
 if save:
  for d in sorted(detections,key=lambda d:d['confidence'],reverse=True):
   if d['type'] not in {r['type'] for r in reports}:
    h=await save_report(Report(type=d['type'],location='Camera detection — GPS location',severity='Medium',lat=lat,lon=lon),u,'camera',d['confidence']);reports.append(h)
 return {'detections':detections,'reports':reports,'image_size':[im.width,im.height],'privacy':'Image processed in memory, not stored','severity_note':'Medium is an unassessed default, not an AI severity prediction'}
@app.get('/api/health')
def health():
 return {'status':'ok','version':'2.5.0','media':{'enabled':True,'max_video_seconds':30,'max_video_mb':20,'max_photo_mb':5,'max_attachments':3},'database':'PostgreSQL/PostGIS' if URL.startswith('postgresql') else 'SQLite','ai':{'configured':bool(MODEL_PATH and Path(MODEL_PATH).is_file()),'loaded':MODEL is not None},'routing':'live external providers','limitations':['Bundled pothole model is third-party and not locally field-validated','No background GPS tracking','No certified navigation or emergency feed']}
@app.websocket('/api/events')
async def events(ws:WebSocket):
 await ws.accept()
 try:
  frame=await asyncio.wait_for(ws.receive_json(),timeout=10);read_token(frame.get('token',''));connections.add(ws);await ws.send_json({'event':'connected'})
  while True:
   msg=await asyncio.wait_for(ws.receive_text(),timeout=90)
   if msg=='ping':await ws.send_json({'event':'pong'})
 except (WebSocketDisconnect,HTTPException,asyncio.TimeoutError,ValueError,KeyError):pass
 finally:
  connections.discard(ws)
  try:await ws.close()
  except RuntimeError:pass

from media_routes import install_media_routes
install_media_routes(app,current,lambda image,confidence:inference(image,confidence),Report,broadcast,throttle,frame_slots)

if os.getenv('SERVE_WEB')=='1':
 from fastapi.staticfiles import StaticFiles
 web=BASE.parent/'dist'
 if web.is_dir():app.mount('/',StaticFiles(directory=web,html=True),name='web')

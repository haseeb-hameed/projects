import os,sys,io
from pathlib import Path
os.environ['DATABASE_URL']='sqlite://'
os.environ['JWT_SECRET']='test-secret-not-for-deployment-123456789'
sys.path.insert(0,str(Path(__file__).parents[1]/'backend'))
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine
import models
# A single in-memory connection across TestClient threads.
engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
models.engine=engine;models.Session.configure(bind=engine);models.Base.metadata.create_all(engine)
import main,providers
from geo import distance,bearing,segment_distance,risk_for_path,graph_search
from PIL import Image
client=TestClient(main.app)
@pytest.fixture(autouse=True)
def reset():
 models.Base.metadata.drop_all(engine);models.Base.metadata.create_all(engine);main.limits.clear();main.MODEL_PATH='';main.MODEL=None;main.camera_sessions.sessions.clear()

def account(n=1):
 r=client.post('/api/auth/register',json={'name':f'Tester {n}','email':f'test{n}@example.com','password':'testpass123'});assert r.status_code==200,r.text
 return {'Authorization':'Bearer '+r.json()['token']}
def report(headers,**kwargs):
 payload={'type':'Pothole','location':'Test Road','severity':'Medium','lat':10.78,'lon':76.65}|kwargs
 r=client.post('/api/hazards',headers=headers,json=payload);assert r.status_code==200,r.text;return r.json()

def test_health_empty():
 r=client.get('/api/health');assert r.json()['ai']['configured'] is False;assert client.get('/api/hazards').json()==[]
def test_auth_login_duplicate_and_bad_password():
 account();assert client.post('/api/auth/register',json={'name':'Test','email':'test1@example.com','password':'testpass123'}).status_code==409
 assert client.post('/api/auth/login',json={'email':'test1@example.com','password':'wrong'}).status_code==401
 r=client.post('/api/auth/login',json={'email':'test1@example.com','password':'testpass123'});assert r.status_code==200
 assert client.get('/api/auth/me',headers={'Authorization':'Bearer '+r.json()['token']}).json()['name']=='Tester 1'
def test_auth_required_and_validation():
 assert client.post('/api/hazards',json={}).status_code==401
 assert client.get('/api/auth/me',headers={'Authorization':'Bearer fake'}).status_code==401
 assert client.post('/api/auth/register',json={'name':'ab','email':'invalid','password':'short'}).status_code==422
 h=account();assert client.post('/api/hazards',headers=h,json={'type':'Pothole','location':'Road','lat':100,'lon':76}).status_code==422
def test_report_persist_nearby():
 a=account();h=report(a);assert client.get('/api/hazards').json()[0]['id']==h['id']
 assert len(client.get('/api/hazards?lat=10.78&lon=76.65&radius=50').json())==1
 assert client.get('/api/hazards?lat=0&lon=0&radius=50').json()==[]
def test_own_confirmation_and_duplicate():
 a,b=account(),account(2);h=report(a)
 assert client.post(f"/api/hazards/{h['id']}/confirm",headers=a).status_code==409
 assert client.post(f"/api/hazards/{h['id']}/confirm",headers=b).status_code==200
 assert client.post(f"/api/hazards/{h['id']}/confirm",headers=b).status_code==409
 assert client.get('/api/hazards').json()[0]['confirmations']==1

def test_clear_threshold_and_owner_clear():
 a,b,c=account(),account(2),account(3);h=report(a)
 assert client.post(f"/api/hazards/{h['id']}/clear",headers=b).json()['status']=='reported'
 assert client.post(f"/api/hazards/{h['id']}/clear",headers=c).json()['status']=='cleared'
 assert client.get('/api/hazards').json()==[]
 h=report(a);assert client.post(f"/api/hazards/{h['id']}/clear",headers=a).json()['status']=='cleared'
def test_confirmed_status_and_vote_change():
 a,b,c=account(),account(2),account(3);h=report(a)
 client.post(f"/api/hazards/{h['id']}/confirm",headers=b)
 assert client.post(f"/api/hazards/{h['id']}/confirm",headers=c).json()['status']=='confirmed'
 r=client.post(f"/api/hazards/{h['id']}/clear",headers=c).json();assert r['clear_votes']==1 and r['confirmations']==1

def test_heading_alerts_and_accuracy():
 a=account();report(a,lat=10.783,lon=76.65)
 def alerts(**kw):return client.post('/api/alerts',headers=a,json={'lat':10.78,'lon':76.65,'heading':0,'accuracy':10}|kw).json()['alerts']
 assert len(alerts())==1;assert alerts(heading=180)==[];assert alerts(accuracy=100)==[];assert len(alerts(heading=None))==1

def test_expiry_and_zone():
 a=account();h=report(a,type='Flood',severity='High');assert len(client.get('/api/zones').json())==1
 with models.Session() as s:
  row=s.get(models.Hazard,h['id']);row.expires=0;s.commit()
 assert client.get('/api/hazards').json()==[];assert client.get('/api/zones').json()==[]
def test_geometry():
 assert 110<distance((0,0),(.001,0))<112;assert bearing((0,0),(1,0))==0
 assert segment_distance((0,.001),(0,0),(0,.002))<1
 h={'type':'Flood','severity':'High','lat':10,'lon':76};risk=risk_for_path([[75.999,10],[76.001,10]],[h]);assert risk['blocked']
 assert not risk_for_path([[75,9],[75.01,9]],[h])['blocked']
def test_astar_dijkstra_same_optimum():
 pos={'a':(0,0),'b':(0,.001),'c':(.001,0),'d':(.001,.001)}
 graph={'a':[('b',200),('c',120)],'c':[('d',120)],'b':[('d',200)]}
 for algorithm in ['astar','dijkstra']:
  path,cost,_=graph_search(graph,'a','d',pos,algorithm);assert path==['a','c','d'];assert cost==240
 assert graph_search({},'a','d',pos)[0] is None

def test_real_provider_contract_and_closure_rank(monkeypatch):
 a=account();report(a,type='Blocked road',severity='High')
 async def fake(*args,**kwargs):return {'code':'Ok','routes':[{'distance':500,'duration':90,'geometry':{'coordinates':[[76.649,10.78],[76.651,10.78]]},'legs':[{'steps':[]}]},{'distance':700,'duration':120,'geometry':{'coordinates':[[76.649,10.79],[76.651,10.79]]},'legs':[{'steps':[]}]}]}
 monkeypatch.setattr(providers,'get_json',fake)
 res=client.post('/api/routes',json={'origin_lat':10.78,'origin_lon':76.649,'dest_lat':10.78,'dest_lon':76.651}).json()
 assert res['routes'][0]['recommended'];assert res['routes'][1]['blocked'];assert res['routes'][0]['distance']==700

def test_provider_failure_not_simulated(monkeypatch):
 from fastapi import HTTPException
 async def fail(*args,**kwargs):raise HTTPException(503,'Provider unavailable')
 monkeypatch.setattr(providers,'get_json',fail)
 r=client.post('/api/routes',json={'origin_lat':10.78,'origin_lon':76.64,'dest_lat':10.79,'dest_lon':76.65});assert r.status_code==503

def image_bytes():
 b=io.BytesIO();Image.new('RGB',(30,20)).save(b,format='JPEG');return b.getvalue()
def test_no_model_is_explicit_and_bad_images_rejected():
 a=account();data={'lat':'10.78','lon':'76.65','accuracy':'10','save':'true'}
 r=client.post('/api/detect',headers=a,data=data,files={'image':('road.jpg',image_bytes(),'image/jpeg')});assert r.status_code==503
 assert client.get('/api/hazards').json()==[]
 r=client.post('/api/detect',headers=a,data=data,files={'image':('road.jpg',b'fake','image/jpeg')});assert r.status_code==422

def test_inference_pipeline_and_spatial_dedup(monkeypatch):
 a=account();monkeypatch.setattr(main,'inference',lambda im:[{'type':'Pothole','class':'pothole','confidence':.9,'box':[1,2,10,12]}])
 args={'headers':a,'data':{'lat':'10.78','lon':'76.65','accuracy':'10','save':'true'},'files':{'image':('road.jpg',image_bytes(),'image/jpeg')}}
 first=client.post('/api/detect',**args).json();second=client.post('/api/detect',**args).json()
 assert first['reports'][0]['source']=='camera';assert second['reports'][0]['deduplicated'];assert len(client.get('/api/hazards').json())==1

def test_websocket_reports():
 a=account()
 with client.websocket_connect('/api/events') as ws:
  ws.send_json({'token':a['Authorization'].split()[1]});assert ws.receive_json()['event']=='connected'
  report(a);assert ws.receive_json()['event']=='hazard_created'
  ws.send_text('ping');assert ws.receive_json()['event']=='pong'

def test_read_only_frame_analysis_needs_no_gps_or_account(monkeypatch):
 seen=[]
 def fake(im,confidence):
  seen.append(confidence);return [{'type':'Pothole','class':'0','confidence':.64,'box':[1,2,10,12]}]
 monkeypatch.setattr(main,'inference',fake)
 r=client.post('/api/vision/frame',data={'source':'video','frame_id':'17','confidence':'.3'},files={'image':('frame.jpg',image_bytes(),'image/jpeg')})
 assert r.status_code==200,r.text
 data=r.json();assert data['frame_id']==17 and data['source']=='video';assert data['detections'][0]['confidence']==.64
 assert data['saved'] is False and data['reports']==[];assert seen==[.3];assert client.get('/api/hazards').json()==[]

def test_frame_invalid_inputs_and_model_errors(monkeypatch):
 r=client.post('/api/vision/frame',data={'confidence':'.99'},files={'image':('frame.jpg',image_bytes(),'image/jpeg')});assert r.status_code==422
 r=client.post('/api/vision/frame',files={'image':('frame.jpg',b'not-image','image/jpeg')});assert r.status_code==422
 r=client.post('/api/vision/frame',files={'image':('frame.jpg',image_bytes(),'image/jpeg')});assert r.status_code==503
 assert client.get('/api/hazards').json()==[]

# Phone-camera integration tests use synthetic frames and explicit fake inference.
# They validate the reporting pipeline, NOT camera hardware or detector accuracy.
def mobile_request(headers,sequence,**extra):
 import time
 t=time.time();data={'session_id':'phone_test_session_12345','sequence':str(sequence),'captured_at':str(t),'gps_at':str(t-1),'lat':'10.783','lon':'76.65','accuracy':'12','share':'true'}|extra
 return client.post('/api/mobile/frame',headers=headers,data=data,files={'image':('phone.jpg',image_bytes(),'image/jpeg')})
def stable_detector(im,confidence):return [{'type':'Pothole','confidence':.85,'class':'0','box':[1,2,20,18]}]

def test_phone_stable_detection_saves_then_alerts_another_user(monkeypatch):
 monkeypatch.setattr(main,'inference',stable_detector);a,b=account(),account(2)
 for seq in [1,2]:
  r=mobile_request(a,seq);assert r.status_code==200,r.text;assert r.json()['report_status']=='verifying';assert r.json()['reports']==[]
 r=mobile_request(a,3);assert r.status_code==200,r.text;data=r.json();assert data['report_status']=='saved';assert len(data['reports'])==1
 h=data['reports'][0];assert h['source']=='camera' and h['severity']=='Medium' and h['lat']==10.783
 assert mobile_request(a,4).json()['report_status']=='cooldown';assert len(client.get('/api/hazards').json())==1
 alert=client.post('/api/alerts',headers=b,json={'lat':10.78,'lon':76.65,'accuracy':10,'heading':0}).json()['alerts'][0]
 assert alert['id']==h['id'] and 'ahead' in alert['message']

def test_phone_bad_gps_does_not_publish_but_preserves_detections(monkeypatch):
 monkeypatch.setattr(main,'inference',stable_detector);a=account()
 for seq in [1,2,3]:
  d=mobile_request(a,seq,accuracy='100').json();assert d['report_status']=='gps_unreliable';assert d['detections']
 assert client.get('/api/hazards').json()==[]
 assert mobile_request(a,4).json()['report_status']=='saved'

def test_phone_preview_and_confidence_gate(monkeypatch):
 a=account();monkeypatch.setattr(main,'inference',stable_detector)
 for seq in [1,2,3]:assert mobile_request(a,seq,share='false').json()['report_status']=='preview_only'
 assert client.get('/api/hazards').json()==[]
 main.camera_sessions.sessions.clear()
 monkeypatch.setattr(main,'inference',lambda im,c:[{'type':'Pothole','confidence':.50,'class':'0','box':[1,2,20,18]}])
 for seq in [1,2,3,4]:assert mobile_request(a,seq).json()['report_status']=='no_eligible_detection'
 assert client.get('/api/hazards').json()==[]

def test_phone_sequence_stop_and_account_isolation(monkeypatch):
 monkeypatch.setattr(main,'inference',stable_detector);a,b=account(),account(2)
 assert mobile_request(a,1).status_code==200;assert mobile_request(a,1).status_code==409
 assert client.post('/api/mobile/session/phone_test_session_12345/stop',headers=a).json()['stopped']
 assert mobile_request(a,2).status_code==409
 assert mobile_request(b,1).status_code==200
 assert mobile_request({},1).status_code==401

def test_phone_timestamps_and_recovery_after_model_error(monkeypatch):
 import time
 a=account();assert mobile_request(a,1,captured_at=str(time.time()-200)).status_code==422
 assert mobile_request(a,1).status_code==503
 assert not main.camera_sessions.sessions[(1,'phone_test_session_12345')].busy
 monkeypatch.setattr(main,'inference',stable_detector);assert mobile_request(a,2).status_code==200

def test_phone_stop_during_inference_prevents_report(monkeypatch):
 a=account();monkeypatch.setattr(main,'inference',stable_detector);mobile_request(a,1);mobile_request(a,2)
 def stop_while_processing(im,c):
  main.camera_sessions.end(1,'phone_test_session_12345');return stable_detector(im,c)
 monkeypatch.setattr(main,'inference',stop_while_processing)
 r=mobile_request(a,3);assert r.json()['report_status']=='stopped';assert client.get('/api/hazards').json()==[]

def test_temporal_gate_resets_on_gap_motion_and_missing_detection():
 from mobile_tracking import CameraSession
 session=CameraSession();d=stable_detector(None,None)
 assert session.observe(d,(30,20),1)==[];assert session.observe(d,(30,20),2)==[];assert session.observe(d,(30,20),3)
 assert session.observe(d,(30,20),10)==[];assert session.tracks['Pothole']['count']==1
 session.observe([],(30,20),11);assert session.tracks=={}
 far=[{'type':'Pothole','confidence':.9,'box':[25,0,30,4]}]
 session.observe(d,(30,20),12);session.observe(far,(30,20),13);assert session.tracks['Pothole']['count']==1

def test_phone_second_session_uses_spatial_dedup(monkeypatch):
 monkeypatch.setattr(main,'inference',stable_detector);a=account()
 for seq in [1,2,3]:mobile_request(a,seq)
 for seq in [1,2,3]:r=mobile_request(a,seq,session_id='phone_second_session_12345')
 assert r.json()['report_status']=='deduplicated';assert len(client.get('/api/hazards').json())==1

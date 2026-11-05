"""Bounded, per-user camera sessions and a simple temporal detection gate.
Not a calibrated tracker. State is intentionally process-local for this prototype.
"""
from dataclasses import dataclass, field
import time

def normalized(box,size):
 w,h=size
 return (box[0]/w,box[1]/h,box[2]/w,box[3]/h)
def iou(a,b):
 intersection=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
 return intersection/max(1e-9,(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-intersection)
@dataclass
class CameraSession:
 sequence:int=0
 busy:bool=False
 enabled:bool=True
 touched:float=field(default_factory=time.monotonic)
 tracks:dict=field(default_factory=dict)
 shared:dict=field(default_factory=dict)
 def observe(self,detections,size,captured_at):
  candidates={}
  for d in detections:
   if d['confidence']>=.60 and (d['type'] not in candidates or d['confidence']>candidates[d['type']]['confidence']):candidates[d['type']]=d
  updated={};eligible=[]
  for kind,d in candidates.items():
   box=normalized(d['box'],size);old=self.tracks.get(kind);count=1
   if old and 0<captured_at-old['at']<=5 and iou(box,old['box'])>=.20:count=old['count']+1
   updated[kind]={'box':box,'at':captured_at,'count':count}
   if count>=3:eligible.append(d)
  self.tracks=updated;self.touched=time.monotonic()
  return eligible
class SessionError(Exception):pass
class CameraSessions:
 def __init__(self,maximum=512):self.sessions={};self.maximum=maximum
 def begin(self,user_id,session_id,sequence):
  t=time.monotonic()
  for key in list(self.sessions):
   state=self.sessions[key]
   if not state.busy and t-state.touched>600:del self.sessions[key]
  key=(user_id,session_id)
  if key not in self.sessions:
   if len(self.sessions)>=self.maximum:raise SessionError('Camera session capacity reached. Retry later.')
   own=[k for k,v in self.sessions.items() if k[0]==user_id and not v.busy]
   if len(own)>=4:del self.sessions[min(own,key=lambda k:self.sessions[k].touched)]
   self.sessions[key]=CameraSession()
  state=self.sessions[key]
  if not state.enabled:raise SessionError('This camera session has been stopped. Start a new session.')
  if state.busy:raise SessionError('A frame from this camera session is still processing.')
  if sequence<=state.sequence:raise SessionError('Out-of-order or repeated camera frame rejected.')
  state.sequence=sequence;state.busy=True;state.touched=t
  return state

 def end(self,user_id,session_id):
  key=(user_id,session_id)
  if key not in self.sessions:
   if len(self.sessions)>=self.maximum:raise SessionError('Camera session capacity reached.')
   self.sessions[key]=CameraSession(enabled=False)
  self.sessions[key].enabled=False;self.sessions[key].touched=time.monotonic()

import React,{useEffect,useRef,useState}from'react';
import{View,Text,Pressable,StyleSheet,Image,Switch,AppState,ActivityIndicator,Linking}from'react-native';
import{CameraView,useCameraPermissions}from'expo-camera';
import{manipulateAsync,SaveFormat}from'expo-image-manipulator';
import{File}from'expo-file-system';
import{gpsReady,boxLayout,selectPictureSize,cycleDelay}from'./cameraMath';

const STATUS={demo_storage_unavailable:'DEMO storage not ready: retry loading saved potholes',demo_waiting:'DEMO: waiting for a real model detection',demo_verifying:'DEMO: checking repeated pothole detection',demo_saved:'DEMO marker saved on selected route (not community data)',demo_duplicate:'DEMO: marker already exists at this virtual location',demo_no_route:'DEMO: select a route first',preview_only:'Preview only — no reports shared',verifying:'Checking repeated confident detection',no_eligible_detection:'No stable high-confidence hazard yet',gps_unreliable:'GPS weak or stale — reports paused',saved:'Hazard report saved and shared',deduplicated:'Existing nearby report matched — no duplicate',cooldown:'Detection verified — sharing cooldown',stopped:'Camera session stopped'};
function dispose(uri){if(uri){try{new File(uri).delete()}catch{}}}
export default function DriveCamera({demoMode=false,demoPosition=.25,onDemoFrame,api,user,gps,health,onSignIn,onEnableGPS,onReports,onRunning,onPrepareAlerts,speak}){
 const[permission,requestPermission]=useCameraPermissions(),[enabled,EN]=useState(false),[cameraReady,CR]=useState(false),[pictureSize,PS]=useState(),[running,RUN]=useState(false),[busy,B]=useState(false),[share,SH]=useState(true),[error,E]=useState(''),[response,RE]=useState(null),[frame,FR]=useState(null),[count,COUNT]=useState(0),[fps,FPS]=useState(0),[latency,LAT]=useState(0),[layout,LAY]=useState({width:0,height:0}),[stage,STAGE]=useState('');
 const camera=useRef(),live=useRef(true),settings=useRef({}),active=useRef(false),epoch=useRef(0),inFlight=useRef(false),timer=useRef(),request=useRef(),session=useRef(''),sequence=useRef(0),displayedUri=useRef(),timings=useRef([]),failures=useRef(0),lastSpoken=useRef(0);
 settings.current={demoMode,demoPosition,onDemoFrame,api,user,gps,share,health,onReports,onRunning,speak};
 function stop(reason=''){
  const id=session.current;active.current=false;epoch.current++;clearTimeout(timer.current);request.current?.abort();session.current='';if(live.current){RUN(false);if(reason)E(reason)}settings.current.onRunning?.(false);
  if(id&&!settings.current.demoMode)settings.current.api(`mobile/session/${id}/stop`,{method:'POST'}).catch(()=>{});
 }
 useEffect(()=>{live.current=true;const subscription=AppState.addEventListener('change',state=>{if(state!=='active'){stop('Detection stopped because the app left the foreground.');EN(false);CR(false)}});return()=>{stop();live.current=false;subscription.remove();dispose(displayedUri.current)}},[]);
 useEffect(()=>{if(!user&&active.current)stop('Sign in again to continue detection.')},[user]);
 async function prepare(){E('');if(!user&&!demoMode)return onSignIn();try{const p=permission?.granted?permission:await requestPermission();if(!p.granted){E('Rear-camera permission is required. Allow it in Android settings.');return}if(!demoMode)await onEnableGPS();try{await onPrepareAlerts?.()}catch{}if(AppState.currentState!=='active'){E('Return to the app and prepare the camera again.');return}EN(true);CR(false)}catch(e){E(e.message||'Could not prepare the phone camera.')}}
 async function ready(){try{const sizes=await camera.current?.getAvailablePictureSizesAsync();if(live.current)PS(selectPictureSize(sizes))}catch{}finally{if(live.current)CR(true)}}
 async function capture(id){
  if(!active.current||id!==epoch.current||inFlight.current)return;
  inFlight.current=true;B(true);STAGE('Capturing photo');const started=Date.now();let raw,small,retained=false;
  try{
   raw=await camera.current.takePictureAsync({quality:.65,skipProcessing:false,shutterSound:false});
   const capturedAt=Date.now()/1000,fix=settings.current.gps,virtualFraction=settings.current.demoPosition;
   if(id!==epoch.current)return;
   STAGE('Resizing JPEG');
   const factor=Math.min(1,960/Math.max(raw.width,raw.height));
   small=await manipulateAsync(raw.uri,[{resize:{width:Math.max(1,Math.round(raw.width*factor)),height:Math.max(1,Math.round(raw.height*factor))}}],{compress:.72,format:SaveFormat.JPEG});
   if(raw.uri!==small.uri){dispose(raw.uri);raw=null}
   if(id!==epoch.current)return;
   // Expo SDK 58 fetch accepts File/Blob, not the old {uri,name,type} object.
   const body=new FormData();body.append('image',new File(small.uri));const seq=++sequence.current;
   const demo=settings.current.demoMode;
   if(demo){body.append('frame_id',String(seq));body.append('source','camera');body.append('confidence','0.35')}
   else{
    body.append('session_id',session.current);body.append('sequence',String(seq));body.append('captured_at',String(capturedAt));body.append('share',String(settings.current.share));
    if(fix&&Number.isFinite(fix.lat)&&Number.isFinite(fix.lon)){body.append('lat',String(fix.lat));body.append('lon',String(fix.lon));body.append('accuracy',String(Math.max(0,Math.min(10000,fix.accuracy??10000))));body.append('gps_at',String((fix.timestamp||0)/1000))}
   }
   STAGE('Uploading / waiting for backend AI');
   request.current=new AbortController();const timeout=setTimeout(()=>request.current?.abort(),timings.current.length?45000:120000);let data;
   try{data=await settings.current.api(demo?'vision/frame':'mobile/frame',{method:'POST',body,signal:request.current.signal})}finally{clearTimeout(timeout)}
   if(id!==epoch.current||!live.current)return;
   if(demo){if(data.frame_id!==seq)throw Error('Unexpected preview frame response');data={...data,sequence:seq,session_id:session.current,...await settings.current.onDemoFrame?.({...data,demo_fraction:virtualFraction})}}
   if(data.sequence!==seq||data.session_id!==session.current)throw Error('Unexpected camera frame response. Restart detection.');
   const previous=displayedUri.current;displayedUri.current=small.uri;retained=true;FR({uri:small.uri,width:small.width,height:small.height});RE(data);COUNT(n=>n+1);LAT(Date.now()-started);const t=Date.now();timings.current=[...timings.current.slice(-9),t];const ts=timings.current;FPS(ts.length>1?(ts.length-1)*1000/(ts.at(-1)-ts[0]):0);dispose(previous);failures.current=0;E('');
   if(data.reports.length)settings.current.onReports?.();
   if(data.report_status==='saved'&&Date.now()-lastSpoken.current>15000){lastSpoken.current=Date.now();settings.current.speak?.('Road hazard recorded and shared. Keep your attention on the road.')}
   if(active.current)timer.current=setTimeout(()=>capture(id),cycleDelay(started));
  }catch(e){
   if(id!==epoch.current||!live.current)return;
   if(e.status===401||e.status===403||e.status===404||e.status===422||e.status===503){stop(e.message||'Camera service unavailable.');return}
   failures.current++;
   if(failures.current>=3){stop('Detection stopped after 3 failures: '+(e.message||e.name||'Unknown capture/upload error')+'. Check the backend log while safely parked.');return}
   E(e.name==='AbortError'?'Frame timed out; retrying. Run Test backend AI and inspect the backend log.':e.message||'Capture failed; retrying.');
   if(active.current)timer.current=setTimeout(()=>capture(id),Math.min(4000,1000*failures.current));
  }finally{
   if(raw?.uri&&raw.uri!==displayedUri.current)dispose(raw.uri);if(small?.uri&&!retained)dispose(small.uri);inFlight.current=false;if(live.current)B(false);
  }
 }
 async function start(){
  E('');if(!user&&!demoMode)return onSignIn();if(!enabled||!cameraReady)return prepare();if(inFlight.current){E('The previous frame is finishing. Wait briefly and try again.');return}
  if(!health?.ai?.configured){E('No hazard model is configured on the backend. Check the API and model installation.');return}
  if(!demoMode&&share&&!gpsReady(gps)){await onEnableGPS();E('Waiting for a fresh GPS fix with accuracy of 50 m or better. You can disable sharing for preview-only analysis.');return}
  sequence.current=0;failures.current=0;timings.current=[];FPS(0);COUNT(0);session.current='phone_'+Date.now().toString(36)+'_'+Math.random().toString(36).slice(2)+'_'+Math.random().toString(36).slice(2);const id=++epoch.current;active.current=true;RUN(true);settings.current.onRunning?.(true);capture(id);
 }
 const button=(text,fn,primary=false,disabled=false)=><Pressable accessibilityRole="button" disabled={disabled} onPress={fn} style={[styles.button,primary&&styles.primary,disabled&&{opacity:.45}]}><Text style={[styles.buttonText,primary&&{color:'#182a13'}]}>{text}</Text></Pressable>;
 return <View style={styles.root}>
  <View style={styles.notice}><Text style={styles.noticeTitle}>{demoMode?'PRESENTATION · REAL CAMERA INFERENCE / VIRTUAL ROUTE MARKERS':'PHONE REAR CAMERA → ACTUAL BACKEND AI'}</Text><Text style={styles.caption}>Mount the phone securely. Prepare permissions and start before travelling. No manual photos or image selection are needed.</Text></View>
  <View style={styles.row}><View style={styles.status}><Text style={[styles.dot,{color:running?'#c5f36b':'#7b9870'}]}>●</Text><Text style={styles.small}>{running?'AUTOMATIC CAPTURE ACTIVE':enabled?'CAMERA PREPARED':'READY WHEN PARKED'}</Text></View><Text style={styles.gps}>{demoMode?'VIRTUAL ROUTE LOCATION':gpsReady(gps)?`GPS ±${Math.round(gps.accuracy)} m`:'GPS waiting / weak'}</Text></View>
  <View style={styles.liveStage}>
   {enabled&&permission?.granted?<CameraView ref={camera} style={StyleSheet.absoluteFill} facing="back" mode="picture" pictureSize={pictureSize} animateShutter={false} onCameraReady={ready} onMountError={e=>{stop(e.message||'Camera failed to mount');EN(false);CR(false)}}/>:<View style={styles.placeholder}><Text style={styles.placeholderIcon}>◎</Text><Text style={styles.placeholderTitle}>The phone observes the road.</Text><Text style={styles.caption}>Rear camera and foreground location permissions are requested when you prepare detection.</Text></View>}
   <View style={styles.liveLabel}><Text style={styles.overlayText}>LIVE REAR-CAMERA PREVIEW · NO BOXES ON UNPROCESSED FRAMES</Text></View>
  </View>
  <View style={styles.actions}>
   {!enabled?button(demoMode?'Prepare demo camera':'Prepare camera & GPS',prepare,true):button(running?'Stop detection':'Start automatic detection',running?()=>stop():start,!running,!running&&(!cameraReady||busy))}
   {enabled&&!running&&button('Close camera',()=>{stop();EN(false);CR(false)})}
   {!user&&button('Sign in',onSignIn)}
  </View>
  {!demoMode&&<View style={styles.shareRow}><View style={{flex:1}}><Text style={styles.label}>Automatically share GPS-tagged hazards</Text><Text style={styles.tiny}>Turn off for preview only. No recorded-video or synthetic GPS reporting.</Text></View><Switch accessibilityLabel="Automatically share GPS-tagged hazards" value={share} onValueChange={SH} trackColor={{false:'#394b32',true:'#8bb458'}} thumbColor={share?'#d9f7ab':'#a4b197'}/></View>}
  {error?<View style={styles.error}><Text style={styles.errorText}>{error}</Text>{permission&&!permission.canAskAgain&&button('Open Android settings',()=>Linking.openSettings())}</View>:null}
  <View style={styles.reportStatus}><Text style={styles.label}>{response?STATUS[response.report_status]||response.report_status:'Awaiting first analysed camera frame'}</Text><Text style={styles.tiny}>{demoMode?'DEMO ONLY: ≥0.35 confidence in 2 overlapping frames within 15 s. Marker uses the selected virtual route position; no community write.':'Server requires ≥0.60 confidence in 3 successive overlapping frames, then a 10-second per-type reporting cooldown. Matching GPS reports are deduplicated.'}</Text></View>
  <View style={styles.stats}>{[[String(count),'FRAMES'],[fps?fps.toFixed(1):'—','MEASURED FPS'],[latency?String(latency):'—','ROUND TRIP MS']].map(([n,label])=><View key={label}><Text style={styles.statValue}>{n}</Text><Text style={styles.statLabel}>{label}</Text></View>)}</View>
  <View style={styles.analysed} onLayout={e=>LAY({width:e.nativeEvent.layout.width,height:e.nativeEvent.layout.height})}>
   {frame?<Image source={{uri:frame.uri}} style={StyleSheet.absoluteFill} resizeMode="contain"/>:<View style={styles.placeholder}><Text style={styles.placeholderTitle}>Analysed frame appears here.</Text><Text style={styles.caption}>Red boxes will come from actual model results. No example detections are inserted.</Text></View>}
   {frame&&response?.detections.map((d,i)=>{const rect=boxLayout(d.box,response.image_size,layout);return rect?<View pointerEvents="none" key={i} style={[styles.box,rect]}><Text numberOfLines={1} style={styles.boxLabel}>{d.type.toLowerCase()} {d.confidence.toFixed(2)}</Text></View>:null})}
   <View style={styles.analysedLabel}><Text style={styles.overlayText}>EXACT ANALYSED FRAME · NOT A LIVE-IMAGE OVERLAY</Text></View>
   {busy&&<View style={styles.processing}><ActivityIndicator size="small" color="#c5f36b"/><Text style={styles.small}>{stage||'Processing next frame'}</Text></View>}
  </View>
  {response&&<View style={styles.results}><Text style={styles.label}>{response.detections.length} detection(s) · frame {response.sequence}</Text>{response.detections.map((d,i)=><Text key={i} style={styles.caption}>{d.type}: {d.confidence.toFixed(2)} confidence · verification {response.verification_counts?.[d.type]||0}/{demoMode?2:3}</Text>)}<Text style={styles.tiny}>Backend processing {response.inference_ms} ms. No detection does not prove the road is safe.</Text></View>}
  <Text style={styles.caption}>Uses phone camera + network backend, not on-device inference. Capture is sequential without a fixed 5.5-second delay; at most 2.5 requests/s, usually slower. It stops when you change tabs or leave the app.</Text>
  <Text style={styles.caption}>Only potholes are supported by the bundled model. GPS is the camera capture position, not projected object location. Severity is Medium / unassessed. Raw frames are temporary app-cache files and are not retained by the backend. Stop is best-effort: an already committed report is not undone.</Text>
 </View>
}
const styles=StyleSheet.create({root:{gap:14},notice:{backgroundColor:'#22321f',borderWidth:1,borderColor:'#425e34',borderRadius:12,padding:17},noticeTitle:{color:'#c5f36b',fontSize:10,fontWeight:'700',letterSpacing:.7},caption:{color:'#9cb78b',fontSize:11,lineHeight:19,marginTop:8},tiny:{fontSize:9,color:'#89a378',lineHeight:17,marginTop:7},row:{flexDirection:'row',justifyContent:'space-between',gap:10,alignItems:'center'},status:{flexDirection:'row',alignItems:'center',gap:7,flex:1},dot:{fontSize:12},small:{fontSize:8,color:'#b9cfa8'},gps:{fontSize:9,color:'#abc78e'},liveStage:{height:235,backgroundColor:'#0c160f',borderWidth:1,borderColor:'#3b4f31',borderRadius:12,overflow:'hidden'},placeholder:{flex:1,alignItems:'center',justifyContent:'center',padding:24},placeholderIcon:{fontSize:38,color:'#9bbb7e',marginBottom:13},placeholderTitle:{fontSize:15,color:'#c5dbb2',fontWeight:'500',textAlign:'center'},liveLabel:{position:'absolute',left:9,right:9,top:10,backgroundColor:'#102110d9',padding:8,borderRadius:5},overlayText:{fontSize:6,color:'#c3d7b1',letterSpacing:.45},actions:{flexDirection:'row',gap:9,flexWrap:'wrap'},button:{borderWidth:1,borderColor:'#4b623a',borderRadius:9,paddingVertical:14,paddingHorizontal:16,alignItems:'center'},primary:{backgroundColor:'#c5f36b',borderColor:'#c5f36b',flexGrow:1},buttonText:{fontSize:11,fontWeight:'700',color:'#c4dbae'},shareRow:{flexDirection:'row',gap:14,alignItems:'center',backgroundColor:'#1b291b',borderWidth:1,borderColor:'#3a5030',padding:15,borderRadius:10},label:{fontSize:11,color:'#caddb8',fontWeight:'600',lineHeight:19},error:{backgroundColor:'#3a2b20',borderWidth:1,borderColor:'#7a5938',padding:14,borderRadius:9,gap:10},errorText:{fontSize:11,color:'#efbd91',lineHeight:20},reportStatus:{padding:14,borderWidth:1,borderColor:'#425633',backgroundColor:'#202c1d',borderRadius:9},stats:{flexDirection:'row',justifyContent:'space-around',borderWidth:1,borderColor:'#3b4f31',padding:17,borderRadius:10,backgroundColor:'#1b261a'},statValue:{fontSize:25,color:'#d2e6bb',fontWeight:'500'},statLabel:{fontSize:6,color:'#90a77b',letterSpacing:.5,marginTop:7},analysed:{height:340,backgroundColor:'#080e0a',borderWidth:1,borderColor:'#3b4f31',borderRadius:12,overflow:'hidden'},analysedLabel:{position:'absolute',top:10,left:9,right:9,padding:8,backgroundColor:'#102110d9',borderRadius:5},box:{position:'absolute',borderWidth:2,borderColor:'#ff554d'},boxLabel:{position:'absolute',left:-2,top:-17,backgroundColor:'#ff554d',color:'#fff',fontSize:10,fontWeight:'700',paddingHorizontal:3,paddingVertical:1,minWidth:80},processing:{position:'absolute',bottom:10,right:10,flexDirection:'row',alignItems:'center',gap:8,backgroundColor:'#142610e6',padding:9,borderRadius:6},results:{borderWidth:1,borderColor:'#3b4f31',borderRadius:10,padding:15,backgroundColor:'#19261b'}});

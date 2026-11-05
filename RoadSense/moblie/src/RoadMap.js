import React,{forwardRef,useImperativeHandle,useRef,useEffect,useMemo,useState}from'react';
import{View,Text}from'react-native';
import{WebView}from'react-native-webview';
import assets from './mapAssets';

// Leaflet is embedded locally. Only actual OSM raster tiles require internet.
const html=`<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1"><style>${assets.css}html,body,#map{height:100%;margin:0;background:#dae1d6}#note{position:absolute;z-index:1000;top:6px;left:45px;background:#fff;padding:5px;font:11px sans-serif;display:none}.leaflet-control-attribution{font-size:9px}</style></head><body><div id="map"></div><div id="note">Basemap tiles unavailable; route overlay still works.</div><script>${assets.js}</script><script>
const map=L.map('map').setView([10.7867,76.6548],13),layer=L.layerGroup().addTo(map);
const tiles=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; OpenStreetMap contributors'}).addTo(map);
tiles.on('tileerror',()=>document.getElementById('note').style.display='block');tiles.on('tileload',()=>document.getElementById('note').style.display='none');
const post=(x)=>window.ReactNativeWebView.postMessage(JSON.stringify(x));
map.on('click',e=>post({kind:'pin',lat:e.latlng.lat,lon:e.latlng.lng}));map.on('contextmenu',e=>post({kind:'report',lat:e.latlng.lat,lon:e.latlng.lng}));
function mark(p,text,color,radius=7){if(!p||!Number.isFinite(p.lat)||!Number.isFinite(p.lon))return;const m=L.circleMarker([p.lat,p.lon],{radius,bubblingMouseEvents:false,color:'#fff',weight:2,fillColor:color,fillOpacity:1}).addTo(layer);m.bindTooltip(()=>{const n=document.createElement('span');n.textContent=text;return n})}
window.renderRoad=(s)=>{layer.clearLayers();(s.routes||[]).forEach(r=>L.polyline(r.geometry.map(p=>[p[1],p[0]]),{color:r.blocked?'#c74d35':r.id===s.selected?'#407f13':'#758a94',weight:r.id===s.selected?6:3}).addTo(layer));mark(s.origin,'Start','#268dcc');mark(s.destination,'Destination','#2e8423');(s.hazards||[]).forEach(h=>{mark(h,h.type+' — community report','#da7a29');if(h.closure)L.circle([h.lat,h.lon],{radius:100,color:'#c74d35'}).addTo(layer)});(s.demoReports||[]).forEach(h=>mark(h,'DEMO ONLY: '+h.type+' / virtual route location','#bc42ba',9));mark(s.vehicle,'DEMO virtual vehicle','#175cff',8);if(s.gps&&!s.vehicle)mark(s.gps,'Phone GPS','#175cff');};
window.roadFit=(points)=>{if(points?.length)map.fitBounds(points.map(p=>[p.latitude,p.longitude]),{padding:[25,25],maxZoom:16})};
window.roadCenter=(r)=>map.setView([r.latitude,r.longitude],14);
post({kind:'ready'});
</script></body></html>`;
export default forwardRef(function RoadMap({routes,selected,origin,destination,hazards,gps,demoReports,vehicle,onPin,onReport,style},ref){
 const web=useRef(),ready=useRef(false),pending=useRef(),[error,E]=useState('');
 const state={routes,selected,origin,destination,hazards,gps,demoReports,vehicle};const latest=useRef(state);latest.current=state;
 const source=useMemo(()=>({html,baseUrl:'https://roadsense.local/'}),[]);
 const send=(fn,value)=>{if(ready.current)web.current?.injectJavaScript(`window.${fn}(${JSON.stringify(value)});true;`)};
 useImperativeHandle(ref,()=>({fitToCoordinates(points){pending.current={fn:'roadFit',value:points};send('roadFit',points)},animateToRegion(region){pending.current={fn:'roadCenter',value:region};send('roadCenter',region)}}),[]);
 useEffect(()=>{send('renderRoad',state)},[routes,selected,origin,destination,hazards,gps,demoReports,vehicle]);
 return <View style={[{overflow:'hidden'},style]}><WebView ref={web} source={source} style={{flex:1,backgroundColor:'#dae1d6'}} javaScriptEnabled domStorageEnabled applicationNameForUserAgent="RoadSense/2.3.1" originWhitelist={['*']} setSupportMultipleWindows={false} onMessage={e=>{try{const m=JSON.parse(e.nativeEvent.data);if(m.kind==='ready'){ready.current=true;send('renderRoad',latest.current);if(pending.current)send(pending.current.fn,pending.current.value);else{const r=latest.current.routes?.find(r=>r.id===latest.current.selected);if(r)send('roadFit',r.geometry.map(p=>({latitude:p[1],longitude:p[0]})))}}else if(m.kind==='pin')onPin?.(m);else if(m.kind==='report')onReport?.(m)}catch{}}} onError={e=>E(e.nativeEvent.description||'Map view failed to load')}/>{!!error&&<Text style={{backgroundColor:'#402d20',color:'#ffd7a8',padding:10}}>{error}</Text>}</View>
});

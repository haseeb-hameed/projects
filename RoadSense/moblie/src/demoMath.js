// Presentation-only helpers. Never use virtual coordinates for community writes.
const rad=x=>x*Math.PI/180;
function metres(a,b){const p=rad(a[1]),q=rad(b[1]),d=rad(b[0]-a[0]);const h=Math.sin((q-p)/2)**2+Math.cos(p)*Math.cos(q)*Math.sin(d/2)**2;return 12742000*Math.asin(Math.min(1,Math.sqrt(h)))}
function routeLength(g){return (g||[]).slice(1).reduce((n,p,i)=>n+metres(g[i],p),0)}
function routePoint(g,f){if(!g?.length)return null;let left=routeLength(g)*Math.max(0,Math.min(1,f));for(let i=1;i<g.length;i++){const length=metres(g[i-1],g[i]);if(left<=length&&length>0){const t=left/length;return {lon:g[i-1][0]+(g[i][0]-g[i-1][0])*t,lat:g[i-1][1]+(g[i][1]-g[i-1][1])*t}}left-=length}const p=g.at(-1);return {lon:p[0],lat:p[1]}}
function overlap(a,b){const w=Math.max(0,Math.min(a[2],b[2])-Math.max(a[0],b[0])),h=Math.max(0,Math.min(a[3],b[3])-Math.max(a[1],b[1]));const intersection=w*h;return intersection/Math.max(1e-12,(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-intersection)}
function demoTrack(previous,detections,size,now){const [w,h]=size||[];const d=(detections||[]).filter(d=>d.type==='Pothole'&&d.confidence>=.35&&d.box?.length===4).sort((a,b)=>b.confidence-a.confidence)[0];if(!d||!(w>0&&h>0))return null;const box=d.box.map((n,i)=>n/(i%2?h:w));const matches=previous&&now>=previous.at&&now-previous.at<=15000&&overlap(previous.box,box)>=.2;return {box,at:now,count:matches?previous.count+1:1,detection:d}}
module.exports={routeLength,routePoint,demoTrack};

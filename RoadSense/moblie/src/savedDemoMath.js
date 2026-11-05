// Fixed coordinates, not original route IDs/fractions, determine matches on a new route.
const R=6371000,rad=x=>x*Math.PI/180;
function distance(a,b){const p=rad(a.lat),q=rad(b.lat);const h=Math.sin((q-p)/2)**2+Math.cos(p)*Math.cos(q)*Math.sin(rad(b.lon-a.lon)/2)**2;return 2*R*Math.asin(Math.min(1,Math.sqrt(h)))}
function routePosition(point,geometry,tolerance=50){
 if(!geometry?.length)return null;
 if(geometry.length===1){const cross=distance(point,{lon:geometry[0][0],lat:geometry[0][1]});return cross<=tolerance?{along:0,cross}:null}
 let offset=0,best=null;
 for(let i=1;i<geometry.length;i++){
  const a={lon:geometry[i-1][0],lat:geometry[i-1][1]},b={lon:geometry[i][0],lat:geometry[i][1]},cos=Math.cos(rad((a.lat+b.lat+point.lat)/3));
  const x=rad(b.lon-a.lon)*R*cos,y=rad(b.lat-a.lat)*R,px=rad(point.lon-a.lon)*R*cos,py=rad(point.lat-a.lat)*R;
  const length=distance(a,b),t=Math.max(0,Math.min(1,(px*x+py*y)/(x*x+y*y||1)));
  const projected={lon:a.lon+(b.lon-a.lon)*t,lat:a.lat+(b.lat-a.lat)*t},cross=distance(point,projected);
  if(!best||cross<best.cross)best={along:offset+length*t,cross};offset+=length;
 }
 return best&&best.cross<=tolerance?best:null;
}
function onRoute(records,geometry){return records.flatMap(h=>{const p=routePosition(h,geometry);return p?[{...h,routeAlong:p.along,routeCross:p.cross}]:[]})}
module.exports={distance,routePosition,onRoute};

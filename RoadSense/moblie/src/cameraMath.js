// Pure helpers shared with the Node tests; no camera/GPS behaviour is mocked here.
function gpsReady(gps,now=Date.now()){
 return !!gps&&Number.isFinite(gps.lat)&&Number.isFinite(gps.lon)&&Math.abs(gps.lat)<=90&&Math.abs(gps.lon)<=180&&Number.isFinite(gps.accuracy)&&gps.accuracy>=0&&gps.accuracy<=50&&Number.isFinite(gps.timestamp)&&now-gps.timestamp>=-2000&&now-gps.timestamp<=30000;
}
function fitContain(imageWidth,imageHeight,viewWidth,viewHeight){
 if(!(imageWidth>0&&imageHeight>0&&viewWidth>0&&viewHeight>0))return null;
 const scale=Math.min(viewWidth/imageWidth,viewHeight/imageHeight);
 return {scale,left:(viewWidth-imageWidth*scale)/2,top:(viewHeight-imageHeight*scale)/2};
}
function boxLayout(box,imageSize,viewSize){
 const[w,h]=imageSize,fit=fitContain(w,h,viewSize.width,viewSize.height);
 if(!fit||!Array.isArray(box)||box.length!==4||!box.every(Number.isFinite))return null;
 const x1=Math.max(0,Math.min(w,box[0])),y1=Math.max(0,Math.min(h,box[1])),x2=Math.max(x1,Math.min(w,box[2])),y2=Math.max(y1,Math.min(h,box[3]));
 return {left:fit.left+x1*fit.scale,top:fit.top+y1*fit.scale,width:(x2-x1)*fit.scale,height:(y2-y1)*fit.scale};
}
function selectPictureSize(sizes){
 const valid=(sizes||[]).map(s=>{const m=/^(\d+)x(\d+)$/.exec(s);return m?{name:s,edge:Math.max(Number(m[1]),Number(m[2]))}:null}).filter(Boolean);
 valid.sort((a,b)=>(Math.abs(a.edge-1280)+(a.edge<640?3000:0))-(Math.abs(b.edge-1280)+(b.edge<640?3000:0)));
 return valid[0]?.name;
}
function cycleDelay(start,now=Date.now()){return Math.max(0,400-(now-start));}
module.exports={gpsReady,fitContain,boxLayout,selectPictureSize,cycleDelay};

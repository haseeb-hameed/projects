const test=require('node:test');const assert=require('node:assert/strict');
const{gpsReady,fitContain,boxLayout,selectPictureSize,cycleDelay}=require('../src/cameraMath');
test('GPS needs real finite coordinates, accuracy and a recent timestamp',()=>{
 const now=100000,good={lat:10.78,lon:76.65,accuracy:12,timestamp:now};assert.equal(gpsReady(good,now),true);
 for(const patch of [{accuracy:80},{accuracy:-1},{lat:NaN},{lon:190},{timestamp:now-31000},{timestamp:now+3000}])assert.equal(gpsReady({...good,...patch},now),false);
 assert.equal(gpsReady(null,now),false);
});
test('portrait frame letterboxing and detection overlay stay aligned',()=>{
 const fit=fitContain(480,960,360,340);assert.equal(fit.scale,340/960);assert.equal(fit.top,0);assert.equal(fit.left,95);
 const rect=boxLayout([0,0,480,960],[480,960],{width:360,height:340});assert.deepEqual(rect,{left:95,top:0,width:170,height:340});
});
test('landscape frame letterboxing and clipping',()=>{
 const r=boxLayout([-10,-20,1000,1000],[640,480],{width:320,height:340});assert.deepEqual(r,{left:0,top:50,width:320,height:240});
 assert.equal(boxLayout([0,0,4,4],[0,0],{width:1,height:1}),null);assert.equal(boxLayout([0,NaN,4,4],[640,480],{width:320,height:240}),null);
});
test('camera chooses a moderate available picture size, never an unsupported hardcoded size',()=>{
 assert.equal(selectPictureSize(['4032x3024','1280x960','640x480']),'1280x960');assert.equal(selectPictureSize([]),undefined);assert.equal(selectPictureSize(['bad','640x480']),'640x480');
});
test('capture delay enforces a minimum sequential 400 ms cycle',()=>{assert.equal(cycleDelay(1000,1100),300);assert.equal(cycleDelay(1000,1800),0)});

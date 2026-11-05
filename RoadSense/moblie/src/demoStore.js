// Durable, serialized, phone-local DEMO storage. Never writes community data.
const{distance}=require('./savedDemoMath');
const KEY='@roadsense/saved-demo-potholes/v1',MAX_RECORDS=2000;
function validate(h){
 if(!h||typeof h.id!=='string'||!h.id||h.id.length>120||h.source!=='presentation_only'||h.type!=='Pothole'||!Number.isFinite(h.lat)||!Number.isFinite(h.lon)||Math.abs(h.lat)>90||Math.abs(h.lon)>180||!Number.isFinite(h.confidence)||h.confidence<0||h.confidence>1||!Number.isFinite(h.created))throw Error('Saved DEMO pothole data is invalid. Retry loading; do not clear app data.');
 return {id:h.id,type:'Pothole',source:'presentation_only',lat:h.lat,lon:h.lon,confidence:h.confidence,created:h.created,severity:'Medium',routeLabel:typeof h.routeLabel==='string'?h.routeLabel.slice(0,300):'Original presentation route',...(Number.isFinite(h.fraction)?{fraction:h.fraction}:{})};
}
function decode(raw){
 if(raw===null)return [];
 let d;try{d=JSON.parse(raw)}catch{throw Error('Saved DEMO storage is unreadable. Existing data was not overwritten. Retry loading or explicitly delete all DEMO records.')}
 if(!d||d.schema!==1||!Array.isArray(d.records)||d.records.length>MAX_RECORDS)throw Error('Unsupported DEMO storage format. Existing data was not overwritten.');
 const records=d.records.map(validate);if(new Set(records.map(h=>h.id)).size!==records.length)throw Error('Duplicate saved DEMO IDs. Existing data was not overwritten.');return records;
}
function makeDemoStore(storage,key=KEY){
 let records=null,queue=Promise.resolve();
 const clone=rows=>rows.map(h=>({...h}));
 const run=fn=>{const result=queue.then(fn,fn);queue=result.catch(()=>{});return result};
 async function ensure(){if(records===null)records=decode(await storage.getItem(key))}
 async function commit(next){const raw=JSON.stringify({schema:1,records:next});if(new TextEncoder().encode(raw).byteLength>1500000)throw Error('Saved DEMO storage size limit reached (1.5 MB). Delete unwanted DEMO potholes first.');await storage.setItem(key,raw);records=next;return clone(records)}
 return {
  load:()=>run(async()=>{await ensure();return clone(records)}),
  add:h=>run(async()=>{await ensure();const item=validate(h);const duplicate=records.find(x=>distance(x,item)<30);if(duplicate)return {reports:clone(records),saved:false,record:{...duplicate}};if(records.some(x=>x.id===item.id))throw Error('Duplicate DEMO record ID; retry capture.');if(records.length>=MAX_RECORDS)throw Error('Saved DEMO limit reached (2000). Delete unwanted DEMO potholes first.');return {reports:await commit([...records,item]),saved:true,record:item}}),
  remove:id=>run(async()=>{await ensure();return commit(records.filter(x=>x.id!==id))}),
  // Clearing is allowed only through explicit destructive UI confirmation.
  clear:()=>run(()=>commit([]))
 };
}
module.exports={makeDemoStore,KEY,MAX_RECORDS};

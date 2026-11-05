import os,time,asyncio,math
import xml.etree.ElementTree as ET
import httpx
from fastapi import HTTPException
from geo import distance,risk_for_path,graph_search
NOMINATIM=os.getenv('GEOCODER_URL','https://nominatim.openstreetmap.org').rstrip('/')
OSRM=os.getenv('ROUTER_URL','https://router.project-osrm.org').rstrip('/')
OVERPASS=os.getenv('OVERPASS_URL','https://overpass-api.de/api/interpreter')
HEADERS={'User-Agent':os.getenv('MAP_USER_AGENT','RoadSense-MCA-Prototype/2.0 (educational prototype)')}
cache={}; geocode_lock=asyncio.Lock();last_geocode=0
async def get_json(url,params=None,method='GET',data=None,timeout=35):
 try:
  async with httpx.AsyncClient(timeout=timeout,headers=HEADERS) as c:
   r=await c.request(method,url,params=params,data=data);r.raise_for_status();return r.json()
 except (httpx.HTTPError,ValueError) as e:raise HTTPException(503,'Map provider unavailable. Please retry later; no simulated result was substituted.') from e
async def search(q):
 global last_geocode
 key=('search',q.casefold())
 if key in cache and time.time()-cache[key][0]<3600:return cache[key][1]
 async with geocode_lock:
  # Nominatim public service: no client autocomplete; at most one upstream request/sec.
  if key in cache and time.time()-cache[key][0]<3600:return cache[key][1]
  await asyncio.sleep(max(0,1.1-(time.monotonic()-last_geocode)));last_geocode=time.monotonic()
  rows=await get_json(NOMINATIM+'/search',{'q':q,'format':'jsonv2','limit':5,'countrycodes':'in'})
  out=[{'name':r['display_name'],'lat':float(r['lat']),'lon':float(r['lon'])} for r in rows];cache[key]=(time.time(),out);return out
async def osrm_routes(origin,destination,hazards):
 coords=f'{origin[1]},{origin[0]};{destination[1]},{destination[0]}'
 data=await get_json(OSRM+'/route/v1/driving/'+coords,{'alternatives':'true','steps':'true','overview':'full','geometries':'geojson'})
 if data.get('code')!='Ok':raise HTTPException(422,'No driving route was found for these coordinates.')
 out=[]
 for i,r in enumerate(data['routes']):
  geo=r['geometry']['coordinates'];risk=risk_for_path(geo,hazards)
  steps=[]
  for leg in r['legs']:
   for step in leg['steps']:
    m=step['maneuver'];steps.append({'name':step.get('name') or 'unnamed road','distance':step['distance'],'duration':step['duration'],'type':m['type'],'modifier':m.get('modifier',''),'location':m['location'],'geometry':step['geometry']['coordinates']})
  out.append({'id':str(i),'distance':r['distance'],'duration':r['duration'],'geometry':geo,'steps':steps,**risk,'score':r['duration']+risk['risk']*90})
 out.sort(key=lambda r:(r['blocked'],r['score']))
 for r in out:r['recommended']=not r['blocked'] and r is out[0]
 return {'routes':out,'provider':'OSRM','method':'Risk-ranked OSRM alternatives','warning':'Risk is based only on currently reported hazards, not a safety guarantee. High-severity closures are excluded from recommendation. Alternatives may not include every possible route.','all_blocked':all(r['blocked'] for r in out)}
async def facilities(lat,lon):
 key=('facilities',round(lat,3),round(lon,3))
 if key in cache and time.time()-cache[key][0]<600:return cache[key][1]
 query=f'[out:json][timeout:25];(nwr["amenity"="hospital"](around:8000,{lat},{lon});nwr["emergency"="shelter"](around:8000,{lat},{lon});nwr["social_facility"="shelter"](around:8000,{lat},{lon}););out center tags;'
 try:data=await get_json(OVERPASS,method='POST',data={'data':query},timeout=12)
 except HTTPException:
  # Fallback returns hospitals only. Do not relabel bus shelters as emergency shelters.
  out=await hospital_fallback(lat,lon);cache[key]=(time.time(),out);return out
 out=[]
 for r in data.get('elements',[]):
  p=r.get('center',r);tags=r.get('tags',{})
  if 'lat' not in p:continue
  out.append({'id':str(r['id']),'name':tags.get('name','Unnamed facility'),'type':'hospital' if tags.get('amenity')=='hospital' else 'shelter','lat':p['lat'],'lon':p['lon'],'distance':round(distance((lat,lon),(p['lat'],p['lon']))),'phone':tags.get('phone',tags.get('contact:phone',''))})
 out.sort(key=lambda f:f['distance']);cache[key]=(time.time(),out[:20]);return out[:20]
async def graph_route(origin,destination,hazards,algorithm):
 if distance(origin,destination)>8000:raise HTTPException(422,'The educational graph planner supports trips up to 8 km straight-line. Use road alternatives for longer trips.')
 south=min(origin[0],destination[0])-.012;north=max(origin[0],destination[0])+.012;west=min(origin[1],destination[1])-.012;east=max(origin[1],destination[1])+.012
 key=('graph',round(south,3),round(west,3),round(north,3),round(east,3))
 if key in cache and time.time()-cache[key][0]<3600:data=cache[key][1]
 else:
  query=f'[out:json][timeout:25];way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|service|living_street)(_link)?$"]["access"!~"^(private|no)$"]["motor_vehicle"!="no"]["vehicle"!="no"]({south},{west},{north},{east});(._;>;);out body;'
  try:data=await get_json(OVERPASS,method='POST',data={'data':query},timeout=12)
  except HTTPException:
   try:data=await osm_bbox(south,west,north,east)
   except HTTPException:return await candidate_graph_route(origin,destination,hazards,algorithm)
  cache[key]=(time.time(),data)
 positions={r['id']:(r['lat'],r['lon']) for r in data.get('elements',[]) if r['type']=='node'};graph={};lengths={}
 for way in data.get('elements',[]):
  if way['type']!='way':continue
  tags=way.get('tags',{});oneway=tags.get('oneway') in ('yes','1','true') or tags.get('junction')=='roundabout';reverse=tags.get('oneway')=='-1'
  for a,b in zip(way['nodes'],way['nodes'][1:]):
   if a not in positions or b not in positions:continue
   pa,pb=positions[a],positions[b];length=distance(pa,pb);risk=risk_for_path([[pa[1],pa[0]],[pb[1],pb[0]]],hazards)
   if risk['blocked']:continue
   w=length+risk['risk']*200
   edges=[(b,a)] if reverse else [(a,b)] if oneway else [(a,b),(b,a)]
   for x,y in edges:graph.setdefault(x,[]).append((y,w));lengths[x,y]=length
 if not graph:raise HTTPException(422,'No accessible graph roads found.')
 starts=sorted(graph,key=lambda n:distance(origin,positions[n]))[:5]
 allnodes=set(graph)|{v for edges in graph.values() for v,_ in edges};end=min(allnodes,key=lambda n:distance(destination,positions[n]))
 start=starts[0]
 if distance(origin,positions[start])>700 or distance(destination,positions[end])>700:raise HTTPException(422,'Start or destination is too far from a routable road.')
 path,cost,visited=graph_search(graph,start,end,positions,algorithm)
 if not path:raise HTTPException(422,'No path found within the downloaded area after closure exclusion.')
 geo=[[positions[n][1],positions[n][0]] for n in path];risk=risk_for_path(geo,hazards);length=sum(lengths[a,b] for a,b in zip(path,path[1:]))
 return {'routes':[{'id':algorithm,'distance':length,'duration':None,'geometry':geo,'steps':[],'score':cost,'recommended':True,**risk}],'provider':'OpenStreetMap / Overpass','method':algorithm.upper()+' on downloaded road graph','visited_nodes':visited,'all_blocked':False,'warning':'Educational graph planner: no turn-restriction relations, lane guidance or traffic model. No ETA is estimated. Do not use as production turn-by-turn navigation.'}

async def hospital_fallback(lat,lon):
 global last_geocode
 dlat=8000/111320;dlon=dlat/max(.15,math.cos(math.radians(lat)))
 async with geocode_lock:
  await asyncio.sleep(max(0,1.1-(time.monotonic()-last_geocode)));last_geocode=time.monotonic()
  rows=await get_json(NOMINATIM+'/search',{'q':'hospital','format':'jsonv2','limit':20,'bounded':1,'viewbox':f'{lon-dlon},{lat+dlat},{lon+dlon},{lat-dlat}'})
 out=[]
 for r in rows:
  if r.get('type')!='hospital':continue
  la,lo=float(r['lat']),float(r['lon']);dist=distance((lat,lon),(la,lo))
  if dist<=8000:out.append({'id':str(r['osm_id']),'name':r.get('name') or r['display_name'].split(',')[0],'type':'hospital','lat':la,'lon':lo,'distance':round(dist),'phone':'','source':'Nominatim fallback — hospitals only; shelter lookup unavailable'})
 return sorted(out,key=lambda f:f['distance'])
async def osm_bbox(south,west,north,east):
 # A small, read-only OSM extract is a fallback when Overpass is unavailable.
 if (north-south)*(east-west)>.20:raise HTTPException(503,'Graph extract exceeds fallback size limit; use Road alternatives.')
 try:
  async with httpx.AsyncClient(timeout=12,headers=HEADERS) as c:
   r=await c.get('https://www.openstreetmap.org/api/0.6/map',params={'bbox':f'{west},{south},{east},{north}'})
   r.raise_for_status()
   if len(r.content)>20*1024*1024:raise HTTPException(503,'Road extract exceeds 20 MB; select a shorter trip or Road alternatives.')
   root=ET.fromstring(r.content)
 except (httpx.HTTPError,ET.ParseError) as e:raise HTTPException(503,'Road graph providers unavailable. Use Road alternatives or retry later.') from e
 allowed={'motorway','trunk','primary','secondary','tertiary','unclassified','residential','service','living_street'};elements=[]
 for el in root:
  if el.tag=='node':elements.append({'type':'node','id':int(el.attrib['id']),'lat':float(el.attrib['lat']),'lon':float(el.attrib['lon'])})
  elif el.tag=='way':
   tags={t.attrib['k']:t.attrib['v'] for t in el.findall('tag')};road=tags.get('highway','').removesuffix('_link')
   if road not in allowed or tags.get('access') in ('private','no') or tags.get('motor_vehicle')=='no' or tags.get('vehicle')=='no':continue
   elements.append({'type':'way','id':int(el.attrib['id']),'tags':tags,'nodes':[int(n.attrib['ref']) for n in el.findall('nd')]})
 return {'elements':elements,'fallback':'OSM API extract'}

async def candidate_graph_route(origin,destination,hazards,algorithm):
 data=await osrm_routes(origin,destination,hazards)
 paths=[r for r in data['routes'] if not r['blocked']]
 if not paths:raise HTTPException(422,'All candidate roads intersect reported closures; no unblocked path is available.')
 graph={};positions={};lengths={}
 def node(p):
  k=(round(p[1],6),round(p[0],6));positions[k]=k;return k
 for route in paths:
  for a,b in zip(route['geometry'],route['geometry'][1:]):
   u,v=node(a),node(b)
   if u==v:continue
   length=distance(u,v);risk=risk_for_path([a,b],hazards)
   if risk['blocked']:continue
   graph.setdefault(u,[]).append((v,length+risk['risk']*200));lengths[u,v]=length
 start=node(paths[0]['geometry'][0]);end=node(paths[0]['geometry'][-1]);path,cost,visited=graph_search(graph,start,end,positions,algorithm)
 if not path:raise HTTPException(422,'No unblocked route found in the candidate road graph.')
 geo=[[p[1],p[0]] for p in path];risk=risk_for_path(geo,hazards);length=sum(lengths[a,b] for a,b in zip(path,path[1:]))
 return {'routes':[{'id':algorithm,'distance':length,'duration':None,'geometry':geo,'steps':[],'score':cost,'recommended':True,**risk}],'provider':'OSRM road-geometry graph fallback','method':algorithm.upper()+' on OSRM candidate subgraph','visited_nodes':visited,'all_blocked':False,'warning':'Full OSM graph provider unavailable: graph is limited to returned OSRM alternatives, not the entire road network. Educational comparison only; no turn guidance or ETA.'}

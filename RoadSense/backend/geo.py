import math,heapq
EARTH=6371000

def distance(a,b):
 lat1,lon1=a;lat2,lon2=b;p1,p2=map(math.radians,(lat1,lat2));dp=math.radians(lat2-lat1);dl=math.radians(lon2-lon1)
 x=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
 return 2*EARTH*math.asin(min(1,math.sqrt(x)))
def bearing(a,b):
 p1,p2=map(math.radians,(a[0],b[0]));dl=math.radians(b[1]-a[1]);return (math.degrees(math.atan2(math.sin(dl)*math.cos(p2),math.cos(p1)*math.sin(p2)-math.sin(p1)*math.cos(p2)*math.cos(dl)))+360)%360

def segment_distance(point,a,b):
 # Local equirectangular projection; adequate for individual road segments.
 scale=math.cos(math.radians(point[0]));
 def xy(v):return (math.radians(v[1]-point[1])*EARTH*scale,math.radians(v[0]-point[0])*EARTH)
 ax,ay=xy(a);bx,by=xy(b);dx,dy=bx-ax,by-ay;den=dx*dx+dy*dy
 t=max(0,min(1,-(ax*dx+ay*dy)/den)) if den else 0
 return math.hypot(ax+t*dx,ay+t*dy)

def corridor_distance(point,coords):
 return min((segment_distance(point,(a[1],a[0]),(b[1],b[0])) for a,b in zip(coords,coords[1:])),default=float('inf'))

def risk_for_path(coords,hazards):
 matched=[];score=0;blocked=False
 for h in hazards:
  d=corridor_distance((h['lat'],h['lon']),coords)
  radius=100 if h['type'] in ('Flood','Landslide','Blocked road') else 40
  if d<=radius:
   matched.append(h);score+={'Low':1,'Medium':3,'High':7}[h['severity']]
   if h['type'] in ('Flood','Landslide','Blocked road') and h['severity']=='High':blocked=True
 return {'hazards':matched,'risk':score,'blocked':blocked}

def graph_search(graph,start,end,positions,algorithm='astar'):
 # Costs are metres plus non-negative risk penalties. Straight-line heuristic is admissible.
 q=[(0,0,start)];cost={start:0};parents={};visited=0
 while q:
  _,g,node=heapq.heappop(q)
  if g!=cost.get(node):continue
  visited+=1
  if node==end:
   path=[node]
   while path[-1]!=start:path.append(parents[path[-1]])
   return list(reversed(path)),g,visited
  for nxt,w in graph.get(node,[]):
   ng=g+w
   if ng<cost.get(nxt,float('inf')):
    cost[nxt]=ng;parents[nxt]=node
    heuristic=distance(positions[nxt],positions[end]) if algorithm=='astar' else 0
    heapq.heappush(q,(ng+heuristic,ng,nxt))
 return None,float('inf'),visited

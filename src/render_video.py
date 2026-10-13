"""A procedural low-poly club performance. Camera-space meshes; vocal-driven faces."""
from pathlib import Path
from functools import lru_cache
import os, sys, json, math, bisect, subprocess, time
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from choreography import dance_pose

ROOT=Path(__file__).resolve().parents[1]
WORK=Path(os.environ.get('IDCA_WORK_DIR',str(ROOT/'work')));WORK.mkdir(parents=True,exist_ok=True)
DATA=ROOT/'data'
W,H,S,FPS=1920,1080,1.5,30
DURATION=198.76
CUES=json.loads((DATA/('cues.json' if (DATA/'cues.json').exists() else 'source-cues.json')).read_text())
STARTS=[c['start'] for c in CUES]
TRACK=np.load(DATA/'mouth-track.npz') if (DATA/'mouth-track.npz').exists() else None
BEATS=json.loads((DATA/'beats.json').read_text())['beats']
DRUM_BEATS=json.loads((DATA/'percussion-beats.json').read_text())['beats']
TAU=math.tau

# Explicit vocal section bounds prevent the last chorus cue leaking into a bridge/outro.
CHORUSES=[]
for i,cue in enumerate(CUES):
 if cue['section'] in ['Chorus','Final Chorus']:
  if i==0 or CUES[i-1]['section']!=cue['section']:CHORUSES.append([cue['start'],cue['end']])
  else:CHORUSES[-1][1]=cue['end']

def chorus_index(t):
 return next((i for i,(start,end) in enumerate(CHORUSES) if start<=t<end),None)

def dance_section(t):
 # Hold the final chorus entrance still; resume on the return from the head insert.
 if 156<=t<173:return 2
 section=chorus_index(t)
 return section if section in [0,1] else None

def clamp(x):return max(0,min(1,x))
def ease(x):x=clamp(x);return x*x*(3-2*x)
def color(c):return np.array(tuple(int(c[i:i+2],16) for i in (1,3,5))) if isinstance(c,str) else np.array(c)
def blend(a,b,p):return tuple(np.clip(color(a)*(1-p)+color(b)*p,0,255).astype(int))
def rot(rx=0,ry=0,rz=0):
 cx,sx=math.cos(rx),math.sin(rx);cy,sy=math.cos(ry),math.sin(ry);cz,sz=math.cos(rz),math.sin(rz)
 return np.array([[cz,-sz,0],[sz,cz,0],[0,0,1]])@np.array([[cy,0,sy],[0,1,0],[-sy,0,cy]])@np.array([[1,0,0],[0,cx,-sx],[0,sx,cx]])
def mouth(t):return bool(TRACK['open'][min(len(TRACK['open'])-1,max(0,round(t*100)))]) if TRACK is not None else False
def intensity(t):return float(TRACK['energy'][min(len(TRACK['energy'])-1,max(0,round(t*100)))]) if TRACK is not None else .4

CAMERAS={
 'wide':((0,310,920),(0,164,-15),1150),
 'left':((-380,255,760),(0,189,5),1110),
 'right':((380,270,790),(0,194,5),1160),
 'low':((135,130,725),(0,180,10),1120),
 'high':((-80,630,950),(0,150,-45),1170),
 'medium':((-55,270,650),(0,221,15),1150),
 'close':((45,296,470),(0,275,20),1330),
 'profile':((-395,282,450),(0,255,15),1230),
 'studio':((0,245,830),(0,175,20),1300),
 'portrait':((0,277,535),(0,247,15),1300),
 'direct':((0,285,470),(0,279,10),1310),
 'duet':((0,260,820),(0,202,10),1130),
 'overhead':((0,840,630),(0,120,0),1090),
 'desk':((55,325,900),(0,179,60),1130),
}
class Camera:
 def __init__(self,name=None,position=None,target=None,focal=1000,roll=0):
  if name is not None:position,target,focal=CAMERAS[name]
  self.f=focal;self.pos=np.array(position,dtype=float)
  fw=np.array(target)-self.pos;fw/=np.linalg.norm(fw);right=np.cross(fw,[0,1,0]);right/=np.linalg.norm(right);up=np.cross(right,fw)
  if roll:right,up=right*math.cos(roll)+up*math.sin(roll),up*math.cos(roll)-right*math.sin(roll)
  self.mat=np.stack([right,up,fw],axis=1)
 def project(self,pts):
  v=(np.asarray(pts)-self.pos)@self.mat
  return np.stack([640+v[:,0]/v[:,2]*self.f,322-v[:,1]/v[:,2]*self.f],axis=1),v[:,2]
CAMS={k:Camera(k) for k in CAMERAS}

def orbit_camera(t,index):
 # A continuous dolly/crane orbit: low side pass, rising wrap, high sweep, low return.
 points=np.array([(-690,410,840,1010),(-520,170,690,920),(360,260,795,1050),
                  (730,510,690,1000),(60,750,850,1120),(-690,330,780,980),(270,190,805,1050)],float)
 start,end=CHORUSES[index];u=clamp((t-start)/(end-start));q=u*(len(points)-1)
 k=min(len(points)-2,int(q));v=q-k
 a,b,c,d=[points[max(0,min(len(points)-1,j))] for j in [k-1,k,k+1,k+2]]
 p=.5*((2*b)+(-a+c)*v+(2*a-5*b+4*c-d)*v*v+(-a+3*b-3*c+d)*v*v*v)
 if index%2:p[0]*=-1
 target=(25*math.sin(u*TAU),165+10*math.sin(u*TAU),-40)
 return Camera(position=p[:3],target=target,focal=p[3],roll=.032*math.sin(u*TAU))

def nearby_drum(t):return min(DRUM_BEATS,key=lambda b:abs(b-t))

CHORUS_CAMERA_CUTS=[
 [(CHORUSES[0][0],'orbit'),(nearby_drum(55.8),'floor_swoop'),(nearby_drum(59.3),'crane'),(nearby_drum(63.7),'close_arc')],
 [(CHORUSES[1][0],'orbit'),(nearby_drum(105.5),'floor_swoop'),(nearby_drum(109.1),'crane'),(nearby_drum(112.7),'close_arc')],
 [(CHORUSES[2][0],'orbit'),(156,'floor_swoop'),(nearby_drum(159.5),'crane'),(nearby_drum(162.95),'close_arc')],
]

def chorus_camera_shot(t,index):
 cuts=CHORUS_CAMERA_CUTS[index];i=max(0,bisect.bisect_right([c[0] for c in cuts],t)-1)
 start,name=cuts[i];end=cuts[i+1][0] if i+1<len(cuts) else CHORUSES[index][1]
 return name,start,end

def chorus_camera(t,index):
 name,start,end=chorus_camera_shot(t,index);u=ease((t-start)/max(.1,end-start));mirror=-1 if index%2 else 1
 if name=='orbit':return orbit_camera(t,index)
 if name=='floor_swoop':
  # Start at ankle height and look upward, sweeping laterally just above the floor.
  position=(mirror*(-420+790*u),18+70*u*u,650-85*math.sin(math.pi*u)+60*u)
  target=(0,198,0);focal=930+50*u;roll=.025*math.sin(math.pi*u)
 elif name=='crane':
  position=(mirror*(620-980*u),700-270*u,710+140*u)
  target=(0,158,-35);focal=1060;roll=-.025*math.sin(math.pi*u)
 else:
  position=(mirror*(-280+600*u),320-80*u,665-25*u)
  target=(0,203,20);focal=950;roll=.018*math.sin(math.pi*u)
 return Camera(position=position,target=target,focal=focal,roll=roll)

def dance_clock(t):
 i=max(0,bisect.bisect_right(DRUM_BEATS,t)-1)
 start=DRUM_BEATS[i];period=DRUM_BEATS[i+1]-start if i+1<len(DRUM_BEATS) else .44
 return i+clamp((t-start)/max(.001,period))

class Scene:
 def __init__(self,cam):self.cam=cam;self.items=[];self.spot=None
 def poly(self,pts,c,shade=False):
  pts=np.asarray(pts,dtype=float);p,z=self.cam.project(pts)
  if z.min()<2:return
  if shade:
   n=np.cross(pts[1]-pts[0],pts[2]-pts[0]);norm=np.linalg.norm(n)
   if norm>0:n/=norm
   # Neutral front fill preserves faces; colored rims reveal planar geometry.
   light=.55+.37*abs(n[2])+.17*max(0,n[1])
   c=tuple(np.clip(color(c)*light+np.array([3,15,28])*max(0,-n[0])+np.array([20,3,22])*max(0,n[0]),0,255).astype(int))
   if self.spot is not None:
    gel,strength=self.spot;c=blend(c,gel,.26*strength)
  self.items.append((float(z.mean()),0,p,c,0))
 def texture(self,pts,texture):
  p,z=self.cam.project(pts)
  if z.min()>2:self.items.append((float(z.mean())-.1,2,p,texture,0))
 def line(self,pts,c,width=1,bias=.15):
  p,z=self.cam.project(pts)
  if z.min()>2:self.items.append((float(z.mean())-bias,1,p,c,width))
 def paint(self,im):
  d=ImageDraw.Draw(im)
  for _,kind,points,c,width in sorted(self.items,key=lambda i:i[0],reverse=True):
   p=[(round(x*S),round(y*S)) for x,y in points]
   if kind==2:
    xmin=max(0,min(x for x,y in p));ymin=max(0,min(y for x,y in p));xmax=min(W,max(x for x,y in p)+1);ymax=min(H,max(y for x,y in p)+1)
    if xmax<=xmin or ymax<=ymin:continue
    src=[(0,c.height),(c.width,c.height),(c.width,0),(0,0)];mat=[];vals=[]
    for (xx,yy),(uu,vv) in zip(p,src):
     xx-=xmin;yy-=ymin;mat.extend([[xx,yy,1,0,0,0,-uu*xx,-uu*yy],[0,0,0,xx,yy,1,-vv*xx,-vv*yy]]);vals.extend([uu,vv])
    coeff=np.linalg.solve(np.array(mat),np.array(vals));patch=c.transform((xmax-xmin,ymax-ymin),Image.Transform.PERSPECTIVE,coeff,Image.Resampling.BICUBIC)
    im.paste(patch,(xmin,ymin))
   elif kind:d.line(p,fill=c,width=max(1,round(width*S)),joint='curve')
   else:d.polygon(p,fill=c)


def plane(x0,x1,y0,y1,z):return [(x0,y0,z),(x1,y0,z),(x1,y1,z),(x0,y1,z)]
def floor(x0,x1,z0,z1,y=0):return [(x0,y,z0),(x1,y,z0),(x1,y,z1),(x0,y,z1)]
def box(sc,x0,x1,y0,y1,z0,z1,c):
 pts=np.array([(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),(x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)])
 for ids in [(0,3,2,1),(4,5,6,7),(0,4,7,3),(1,2,6,5),(3,7,6,2),(0,1,5,4)]:sc.poly(pts[list(ids)],c,True)

PALETTES={
 'blue':('#060c20','#1a3860','#43dfdf','#8c61ed'),
 'green':('#051619','#14433e','#55e5b5','#7276ec'),
 'purple':('#100a23','#352456','#4ccbd3','#ba64e1'),
}
@lru_cache(maxsize=64)
def background(camname,kind,palette):
 return scene_background(CAMS[camname],kind,palette)

@lru_cache(maxsize=3)
def backdrop(palette):
 dark,light,cyan,purple=PALETTES[palette]
 yy,xx=np.mgrid[0:H:3,0:W:3];xx=xx*3/W;yy=yy*3/H
 glow=np.exp(-(((xx-.5)/.57)**2+((yy-.38)/.53)**2)*2)[...,None]
 arr=color(dark)+(color(light)-color(dark))*glow
 return Image.fromarray(np.uint8(arr)).resize((W,H),Image.Resampling.BILINEAR)

def scene_background(cam,kind,palette):
 dark,light,cyan,purple=PALETTES[palette];im=backdrop(palette).copy()
 sc=Scene(cam)
 if kind=='stage':
  # Folded acoustic panels, floating neon rails and a reflective slate floor.
  for j in range(24):
   x=-1120+j*96;h=430+48*math.sin(j*.73)
   sc.poly([(x,0,-445),(x+48,0,-413),(x+48,h,-413),(x,h,-445)],blend(dark,light,.44))
   sc.poly([(x+48,0,-413),(x+96,0,-445),(x+96,h,-445),(x+48,h,-413)],blend(dark,light,.14))
  for side in [-1,1]:
   for j in range(5):
    x=side*(165+j*94);top=426-j*20;bottom=50+j*12
    sc.line([(x,bottom,-402),(x,top,-402)],blend(dark,cyan if side<0 else purple,.35),9)
    sc.line([(x,bottom,-401),(x,top,-401)],cyan if side<0 else purple,2.4)
  # Offset polygonal light frames form the new club set.
  for shift in [-1,1]:
   pts=[(shift*90-150,90,-408),(shift*90-150,335,-408),(shift*90-82,400,-408),(shift*90+150,400,-408),(shift*90+150,180,-408)]
   sc.line(pts,blend(dark,cyan if shift<0 else purple,.45),8)
   sc.line(pts,cyan if shift<0 else purple,1.6)
  sc.poly(floor(-1500,1500,-500,1100),'#0b1723')
  for z in range(-400,1000,140):sc.line([(-1600,0,z),(1600,0,z)],'#142736',.65)
  for x in range(-1300,1400,200):sc.line([(x,0,-450),(x,0,1000)],'#142736',.6)
  for side in [-1,1]:
   for j in range(5):
    x=side*(165+j*94)
    for z0 in range(-390,360,60):sc.poly(floor(x-4,x+4,z0,z0+38,.3),blend('#0b1723',cyan if side<0 else purple,.09*(1-(z0+400)/800)))
  # Three shallow hexagonal platforms and inset floor lighting.
  for x,z,r in [(0,25,155),(-305,-135,112),(305,-135,112)]:
   pts=[(x+r*math.cos(a),3,z+r*.55*math.sin(a)) for a in np.linspace(0,TAU,7)]
   sc.poly(pts,'#122434');sc.line(pts,blend(cyan,purple,.5),1.1)
  for side in [-1,1]:
   box(sc,side*570-45,side*570+45,0,180,-260,-195,'#111623')
   for y in [49,126]:
    pts=[(side*570+30*math.cos(a),y+30*math.sin(a),-194) for a in np.linspace(0,TAU,9)]
    sc.poly(pts,'#060c13');sc.line(pts,'#273445',1.5)
  # Rigging stays in the scene, correctly changing perspective with each shot.
  sc.line([(-840,545,-260),(840,545,-260)],'#263344',9)
  for x in [-620,-310,310,620]:
   box(sc,x-18,x+18,494,538,-269,-236,'#171e32')
   sc.poly(plane(x-12,x+12,494,503,-234),cyan if x<0 else purple)
  for x in [-360,-180,180,360]:
   box(sc,x-19,x+19,1,25,160,196,'#182637')
   sc.poly(floor(x-13,x+13,166,190,26),'#102438')
 else:
  # Isolated setups: an empty light pool, side-lit portrait, or a geometric alcove.
  sc.poly(floor(-1400,1400,-1000,1200),'#091421')
  for j in range(3):
   r=120+j*35
   pts=[(r*math.cos(a),.5,r*.62*math.sin(a)) for a in np.linspace(0,TAU,65)]
   sc.line(pts,blend(dark,cyan,.14+j*.04),1)
  if kind=='portal':
   for x,c in [(-142,cyan),(142,purple)]:sc.line([(x,0,-95),(x,398,-95)],c,3)
   sc.line([(-142,398,-95),(142,398,-95)],blend(cyan,purple,.5),2)
  elif kind=='split':
   d=ImageDraw.Draw(im);d.rectangle((0,0,W//2,H),fill='#08252e');d.rectangle((W//2,0,W,H),fill='#201436')
   d.line((W//2,0,W//2,H),fill='#69a6b0',width=2)
 sc.paint(im)
 return im

def beat_light(t):
 section=chorus_index(t)
 if section is None:return None,0
 start=max(CHORUSES[section][0],[53.1,102.92,0][section])
 if t<start:return None,0
 i=bisect.bisect_right(DRUM_BEATS,t)-1
 if i<0:return None,0
 if DRUM_BEATS[i]<start:return None,0
 # A brisk onset and soft falloff: one colored bank fires on each measured beat.
 age=t-DRUM_BEATS[i];strength=max(0,1-age/.25)**1.4
 offset=bisect.bisect_left(DRUM_BEATS,start)
 return (i-offset)%2,strength

def lighting(im,cam,t,kind,palette):
 dark,light,cyan,purple=PALETTES[palette]
 ov=Image.new('RGBA',(W,H));d=ImageDraw.Draw(ov)
 sources=[(-620,530,-250),(620,530,-250),(-280,530,-260),(280,530,-260)] if kind=='stage' else [(-230,540,-60),(230,540,-60)]
 for i,source in enumerate(sources):
  xx=180*math.sin(t*.22+i*1.7);zz=70+100*math.cos(t*.15+i)
  p,z=cam.project([source,(xx-95,0,zz),(xx+95,0,zz)])
  if z.min()>2:d.polygon([(round(x*S),round(y*S)) for x,y in p],fill=(*color(cyan if i%2==0 else purple),13 if kind=='stage' else 11))
  p,z=cam.project([(xx+110*math.cos(a),.6,zz+60*math.sin(a)) for a in np.linspace(0,TAU,40)])
  if z.min()>2:d.polygon([(round(x*S),round(y*S)) for x,y in p],fill=(*color(cyan if i%2==0 else purple),12))
 im=Image.alpha_composite(im.convert('RGBA'),ov).convert('RGB')
 bank,power=beat_light(t)
 if power<=0:return im
 # Two independent banks, each containing ceiling downlights and floor uplights.
 gel=('#48efd1','#a079ff')[bank];rgb=tuple(int(v) for v in color(gel))
 fixtures=[((-620,510,-250),(0,0,35)),((310,510,-250),(125,0,20)),((-360,28,180),(10,400,5)),((180,28,180),(-90,400,5))] if bank==0 else [((620,510,-250),(0,0,35)),((-310,510,-250),(-125,0,20)),((360,28,180),(-10,400,5)),((-180,28,180),(90,400,5))]
 beams=Image.new('RGBA',(W,H));bd=ImageDraw.Draw(beams)
 for source,target in fixtures:
  radius=95 if source[1]>100 else 72
  p,z=cam.project([source,(target[0]-radius,target[1],target[2]),(target[0]+radius,target[1],target[2])])
  if z.min()>2:bd.polygon([(round(x*S),round(y*S)) for x,y in p],fill=(*rgb,round(68*power)))
  # Bright lens cores make the alternating banks readable in wide shots.
  p,z=cam.project([source])
  if z[0]>2:
   xx,yy=p[0]*S;r=8 if source[1]<100 else 6
   bd.ellipse((xx-r*3,yy-r*3,xx+r*3,yy+r*3),fill=(*rgb,round(22*power)))
   bd.ellipse((xx-r,yy-r,xx+r,yy+r),fill=(*rgb,round(220*power)))
  if source[1]>100:
   p,z=cam.project([(target[0]+115*math.cos(a),1,target[2]+55*math.sin(a)) for a in np.linspace(0,TAU,33)])
   if z.min()>2:bd.polygon([(round(x*S),round(y*S)) for x,y in p],fill=(*rgb,round(52*power)))
 return Image.alpha_composite(im.convert('RGBA'),beams).convert('RGB')

CAST=[
 dict(skin='#cb987f',jacket='#66518b',pants='#182638',hair='#172531',shirt='#161c2a',accent='#85cfc8',outfit='hoodie',glasses='rectangle'),
 dict(skin='#946d5c',jacket='#e1e3dc',pants='#182535',hair='#181e27',shirt='#e8ece4',accent='#55bca9',outfit='buttondown',glasses='round',gender='woman',hairstyle='long'),
 dict(skin='#dbb2a0',jacket='#3b527c',pants='#1a2137',hair='#b29c92',shirt='#91a4af',accent='#ad91c2',outfit='argyle',glasses=None),
]
class Human:
 def __init__(self,sc,t,x,z,ident,pose,u,cam,scale=1):
  self.sc=sc;self.t=t;self.ident=ident;self.c=CAST[ident];self.scale=scale
  self.outfit=CAST[ident]['outfit'];self.glasses=CAST[ident]['glasses']
  beat=t*2.28*TAU;sw=math.sin(beat*.25+ident*.7)
  self.pos=np.array([x,3+1.8*math.sin(beat*.5+ident),z]);self.pose=pose;self.u=u
  face=math.atan2(cam.pos[0]-x,cam.pos[2]-z)
  self.yaw=face*.67+.07*sw
  self.pitch=.015*math.sin(t*.8);self.roll=.026*sw
  if pose=='walk':self.roll=.045*sw
  if pose=='lean':self.pitch=.10+.035*math.sin(u*1.1)
  if pose=='reach':self.roll=-.035
  if pose=='bow':self.pitch=.18*ease(u/2)
  self.R=rot(self.pitch,self.yaw,self.roll)
  self.headR=rot(.045*math.sin(t*1.2)-(.075 if pose=='rise' else 0),face*.33+.06*math.sin(u*.6),-.03*sw)
  if pose in ['seated','typing','desk_sing']:
   self.pos=np.array([x,-15,z]);self.R=rot(0,.53,0);self.headR=rot(.035,.30,0)
   if pose=='desk_sing':self.headR=rot(.035,-.32+.62*ease((t-187)/2),0)
  if pose in ['run','jump','repair']:
   self.pos=np.array([x,3+abs(math.sin(t*14.3))*5,z]);self.R=rot(.13,1.15,-.035);self.headR=rot(0,-.12,0)
  if pose=='dance':
   section=dance_section(t);section=0 if section is None else section
   first=bisect.bisect_left(DRUM_BEATS,[53.1,102.92,CHORUSES[2][0]][section])
   self.dance=dance_pose(dance_clock(t)-first,section)
   # Both dancers use the formation's facing, without individual yaw or sway offsets.
   face=math.atan2(cam.pos[0],cam.pos[2]-z);self.yaw=face*.67
   self.pos=np.array([x,3.,z])+self.dance['root']
   rx,ry,rz=self.dance['body'];self.dance_yaw=self.yaw+ry
   self.R=rot(rx,self.dance_yaw,rz)
   hx,hy,hz=self.dance['head'];self.headR=rot(hx,face*.33+hy,hz)
 def tr(self,p,head=False):
  p=np.asarray(p,dtype=float)
  if head:p=(p-[0,254,0])@self.headR.T+[0,254,0]
  p=(p-[0,145,0])@self.R.T+[0,145,0]
  return p*self.scale+self.pos
 def poly(self,p,c,shade=True,head=False):self.sc.poly(self.tr(p,head),c,shade)
 def line(self,p,c,width=1,head=False):self.sc.line(self.tr(p,head),c,width)
 def tube(self,a,b,r0,r1,c,n=6):
  a=np.array(a,dtype=float);b=np.array(b,dtype=float);v=b-a;v/=np.linalg.norm(v)
  ref=np.array([0,0,1.]) if abs(v[2])<.9 else np.array([1.,0,0]);e=np.cross(v,ref);e/=np.linalg.norm(e);f=np.cross(v,e)
  rings=[np.array([p+r*(math.cos(q)*e+math.sin(q)*f) for q in np.linspace(0,TAU,n,endpoint=False)]) for p,r in [(a,r0),(b,r1)]]
  for j in range(n):self.poly([rings[0][j],rings[0][(j+1)%n],rings[1][(j+1)%n],rings[1][j]],c)
  self.poly(rings[0],c);self.poly(rings[1],c)
 def solid(self,pts,faces,c,head=False):
  for f in faces:self.poly([pts[k] for k in f],c,True,head)
 def shoe(self,ankle):
  x,y,z=ankle;pts=[(x-12,y-4,z-12),(x+12,y-4,z-12),(x+13,y-4,z+29),(x-13,y-4,z+29),(x-11,y+9,z-11),(x+11,y+9,z-11),(x+12,y+5,z+26),(x-12,y+5,z+26)]
  self.solid(pts,[(0,1,2,3),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0),(4,7,6,5)],'#151c29')
  self.line([(x-13,y-2,z+29),(x+13,y-2,z+29)],'#778d9c',2)
 def hand(self,p,gesture='palm'):
  x,y,z=p;c=self.c['skin']
  self.tube((x,y-9,z),(x,y+8,z),7,8,c,5)
  if gesture=='palm':
   for j in range(4):
    xx=x-5+j*3.5;self.tube((xx,y+5,z+1),(xx+(j-1.5)*1.0,y+16-abs(j-1.5)*2,z+2),2,1.5,c,4)
   self.tube((x+6,y,z),(x+12,y+5,z+2),2.8,2,c,4)
  else:self.tube((x-5,y+4,z+4),(x+6,y+4,z+4),4,3,c,5)
 def draw(self,sings=True,vocal_time=None):
  t=self.t;c=self.c;phase=t*2.28*TAU+self.ident*.4;sw=math.sin(phase*.25)
  # Two articulated legs: hips, knees, ankles and shoes.
  for side in [-1,1]:
   step=math.sin(phase*.5+(0 if side<0 else math.pi))
   stride=24*step if self.pose=='walk' else 4*step
   lift=max(0,step)*(12 if self.pose=='walk' else 1)
   hip=(side*20,146,0);knee=(side*24,79,6+stride*.6);ankle=(side*(30+(8 if self.pose=='open' else 0)),12+lift,stride)
   if self.pose in ['seated','typing','desk_sing']:hip=(side*20,146,0);knee=(side*24,140,65);ankle=(side*25,27,77)
   elif self.pose=='dance':
    i=0 if side<0 else 1;turn=rot(0,self.dance_yaw,0)
    knee=self.dance['knees'][i]@turn.T;ankle=self.dance['feet'][i]@turn.T
    # Keep the feet on the floor during crouches and body rolls, independent of torso lean.
    ankle[1]-=min(0,self.pos[1]-3)/self.scale
    knee=(knee-[0,145,0])@self.R+[0,145,0]
    ankle=(ankle-[0,145,0])@self.R+[0,145,0]
   elif self.pose in ['run','jump']:
    stride=58*step;lift=35*max(0,-step);knee=(side*24,88+lift*.5,stride*.65);ankle=(side*25,13+lift,stride)
   elif self.pose=='repair':
    knee=(side*26,85,20);ankle=(side*32,12,12)
   self.tube(hip,knee,20,14,c['pants']);self.tube(knee,ankle,14,10,c['pants']);self.shoe(ankle)
  # Shared faceted torso, with three distinct programmer wardrobes.
  pts=[(-31,141,-20),(31,141,-20),(49,231,-19),(-49,231,-19),(-32,141,23),(32,141,23),(48,231,24),(-48,231,24),(0,240,17),(0,142,27)]
  self.solid(pts,[(0,3,2,1),(0,4,7,3),(1,2,6,5),(3,7,8,2),(4,5,1,0),(4,9,7),(7,9,8),(5,6,9),(6,8,9)],c['jacket'])
  self.tube((0,230,0),(0,263,0),13,13,c['skin'],6)
  self.draw_outfit()
  # Lead holds a microphone below the mouth; the other arm performs the lyric.
  handR=np.array([26,249,65.]);elbowR=np.array([65,189,31.])
  handL=np.array([-53,147,17.]);elbowL=np.array([-63,187,8.])
  mode=self.pose
  if mode=='heart':handL=np.array([-9,214,51.]);elbowL=np.array([-69,190,27.])
  elif mode in ['open','reach','rise']:
   amount=.5+.5*math.sin(self.u*.9)
   handL=np.array([-119-13*amount,222+(26 if mode=='rise' else -8)*amount,45.]);elbowL=np.array([-87,196,20.])
  elif mode=='hands':handL=np.array([-65,243,67.]);elbowL=np.array([-75,187,29.])
  elif mode=='point':handL=np.array([-98,254,68.]);elbowL=np.array([-84,204,22.])
  elif mode=='lean':handL=np.array([-63,205,60.]);elbowL=np.array([-66,178,15.])
  elif mode=='walk':handL+=np.array([0,8*sw,15*sw])
  elif mode=='bow':handR=np.array([54,155,29.]);elbowR=np.array([66,190,10.]);handL=np.array([-6,205,43.])
  elif mode=='seated':
   handR=np.array([31,161,103.]);elbowR=np.array([61,169,37.]);handL=np.array([-28,156,90.]);elbowL=np.array([-53,170,27.])
  elif mode in ['typing','desk_sing']:
   tap=3 if mode=='typing' else 0
   handR=np.array([31,175+tap*math.sin(t*19),150.]);elbowR=np.array([61,205,49.]);handL=np.array([-28,175+tap*math.sin(t*19+math.pi),148.]);elbowL=np.array([-53,205,49.])
  elif mode=='dance':
   handL,handR,elbowL,elbowR=self.dance['arms']
  elif mode in ['run','jump']:
   swing=math.sin(t*14.3);handR=np.array([51,201+22*swing,48-53*swing]);elbowR=np.array([57,184,12-24*swing]);handL=np.array([-51,201-22*swing,48+53*swing]);elbowL=np.array([-57,184,12+24*swing])
  elif mode=='repair':
   lift=ease(self.u);handR=np.array([42,103+160*lift,83.]);elbowR=np.array([62,157+42*lift,33.]);handL=np.array([-46,148+75*lift,53.]);elbowL=np.array([-62,180,15.])
  for side,elbow,hand in [(-1,elbowL,handL),(1,elbowR,handR)]:
   shoulder=np.array([side*48,225,0.]);sleeve=c['shirt'] if self.outfit=='argyle' else c['jacket']
   wrist=hand-[0,8,0];self.tube(shoulder,elbow,18,13,sleeve);self.tube(elbow,wrist,13,8,sleeve)
   axis=wrist-elbow;axis/=np.linalg.norm(axis)
   self.tube(wrist-axis*9,wrist,10.5,9,blend(sleeve,'#101c30',.22) if self.outfit=='hoodie' else blend(sleeve,'#f0f3eb',.13))
   if mode in ['typing','desk_sing']:
    self.tube(hand+[0,0,-10],hand+[0,0,7],7,7,c['skin'],5)
    for j in range(4):self.tube(hand+[-5+j*3.5,0,5],hand+[-5+j*3.5,-3,17],2,1.5,c['skin'],4)
   else:self.hand(hand,'palm' if mode=='dance' else ('grip' if side>0 else ('palm' if mode in ['open','hands','reach','rise','point','repair'] else 'grip')))
  if mode not in ['seated','typing','desk_sing','dance','run','jump','repair']:
   self.tube(handR+[4,-13,0],handR+[-9,22,0],3.2,4,'#192733',8)
   self.tube(handR+[-9,22,0],handR+[-14,36,0],6.7,6,'#8bafbd',8)
   for dy in [24,28,32]:self.line([handR+[-5-dy*.37,dy,4],handR+[5-dy*.37,dy,4]],'#314652',.7)
  self.draw_head(sings,vocal_time)
 def draw_outfit(self):
  c=self.c
  if self.outfit=='hoodie':
   # A folded hood around the back of the neck, drawstrings, ribbed hem and pouch.
   hood=blend(c['jacket'],'#b1a3c8',.13)
   self.poly([(-43,231,-18),(-34,264,-19),(-18,273,-31),(18,273,-31),(34,264,-19),(43,231,-18)],hood)
   for side in [-1,1]:
    self.poly([(side*42,233,-18),(side*34,264,-19),(side*19,253,14),(side*30,234,27)],hood)
    self.line([(side*34,259,-17),(side*19,250,17),(side*27,235,28)],blend(c['jacket'],'#101c30',.3),2)
   self.poly([(-18,237,27),(18,237,27),(0,222,32)],c['shirt'])
   for side in [-1,1]:
    self.line([(side*12,239,32),(side*14,214,35),(side*17,209,35)],'#c8cbd0',1.4)
    self.line([(side*17,211,35),(side*17,207,35)],'#93e0d1',2)
   pocket=blend(c['jacket'],'#142135',.16)
   self.poly([(-29,167,31),(29,167,31),(25,190,31),(-25,190,31)],pocket)
   self.line([(-29,167,32),(-25,190,32),(25,190,32),(29,167,32)],blend(c['jacket'],'#bdafd0',.22),1)
   self.line([(-26,187,32),(-16,177,34)],c['accent'],1.1);self.line([(26,187,32),(16,177,34)],c['accent'],1.1)
   self.poly([(-32,141,28),(32,141,28),(33,150,29),(-33,150,29)],pocket)
  elif self.outfit=='buttondown':
   self.poly([(-4,145,30),(4,145,30),(4,237,28),(-4,237,28)],blend(c['jacket'],'#ffffff',.20))
   for side in [-1,1]:self.poly([(side*25,234,27),(side*7,242,27),(side*3,223,33),(side*17,216,32)],c['shirt'])
   for y in [219,201,183,165,149]:self.poly([(-1.3,y-1.3,33),(1.3,y-1.3,33),(1.3,y+1.3,33),(-1.3,y+1.3,33)],'#617784',False)
   self.poly([(13,196,31),(34,196,31),(35,221,30),(12,221,30)],blend(c['jacket'],'#7892a1',.12))
   self.line([(12,221,32),(13,196,32),(34,196,32),(35,221,32)],'#879aab',.8)
   for x,h,col in [(18,232,'#234657'),(24,229,c['accent']),(29,234,'#624c83')]:
    self.line([(x,210,33),(x,h,33)],col,2);self.line([(x+2,222,34),(x+2,h-3,34)],col,.8)
  else:
   self.poly([(-24,237,27),(24,237,27),(0,201,32)],c['shirt'])
   for side in [-1,1]:self.poly([(side*24,237,29),(side*6,242,28),(side*2,223,33),(side*13,221,32)],blend(c['shirt'],'#eff5f0',.25))
   self.line([(-27,236,30),(0,198,34),(27,236,30)],blend(c['jacket'],'#101b2c',.35),3)
   for x,y,col in [(-16,179,c['accent']),(16,179,'#73a8aa'),(0,202,'#718ea8'),(0,156,'#718ea8')]:
    self.poly([(x-14,y,32),(x,y+15,32),(x+14,y,32),(x,y-15,32)],col)
   for x in [-16,16]:self.line([(x-14,159,34),(x+14,189,34),(x-14,219,31)],'#acb9c7',.8)
   self.poly([(-32,141,29),(32,141,29),(33,149,30),(-33,149,30)],blend(c['jacket'],'#0f1b2d',.3))
 def draw_head(self,sings=True,vocal_time=None,mouth_open=None):
  t=self.t;c=self.c;mode=self.pose
  # Sculpted, faceted human head. Features share the head transform.
  skin=c['skin'];left=blend(skin,'#69b8bc',.16);right=blend(skin,'#8d72bd',.16)
  verts=[(-16,258,13),(16,258,13),(-27,275,21),(27,275,21),(-31,296,15),(31,296,15),(-26,318,11),(26,318,11),(-13,332,0),(13,332,0),(-20,275,-25),(20,275,-25),(-26,308,-21),(26,308,-21)]
  if c.get('gender')=='woman':
   verts[:4]=[(-12,258,13),(12,258,13),(-24,275,21),(24,275,21)]
  for ids in [(0,2,4,6,8),(1,9,7,5,3),(0,10,12,8),(1,9,13,11),(10,11,13,12),(0,1,11,10),(8,12,13,9)]:self.poly([verts[k] for k in ids],skin,True,True)
  A=(-25,317,20);B=(25,317,20);C=(-23,296,30);D=(23,296,30);E=(0,294,33);F=(-24,277,23);G=(24,277,23);J=(0,272,30);K=(-14,258,16);L=(14,258,16)
  if c.get('gender')=='woman':F=(-22,277,23);G=(22,277,23);K=(-11,258,16);L=(11,258,16)
  for pts,col in [([A,B,E],skin),([A,E,C],left),([B,D,E],right),([C,E,F],skin),([D,G,E],right),([F,E,J],left),([E,G,J],skin),([F,J,K],skin),([J,G,L],right),([K,J,L],skin)]:self.poly(pts,col,True,True)
  for side in [-1,1]:
   self.poly([(side*29,294,9),(side*35,291,7),(side*34,279,6),(side*27,279,12)],skin,True,True)
  # Angular swept hair, with separate silhouettes for all three performers.
  hair=c['hair'];top=345 if self.ident==0 else (342 if self.ident==1 else 338)
  hp=[(-29,307,-19),(29,307,-19),(-30,323,16),(28,323,16),(-18,top,-8),(17,top-3,-9),(-13,333,24),(27,325,24),(-29,321,20)]
  if c.get('hairstyle')=='long':self.draw_long_hair()
  else:
   for ids in [(0,1,5,4),(0,4,6,8),(1,3,7,5),(4,5,7,6),(6,7,3,2),(2,8,6),(0,8,2),(1,0,2,3)]:self.poly([hp[k] for k in ids],hair,True,True)
  if self.ident==2:self.poly([(-25,323,21),(8,335,27),(22,318,26),(-11,307,32)],hair,True,True)
  # Eyelids and eyebrows stay quiet and expressive; mouth has exactly two states.
  blink_phase=0 if mode=='dance' else self.ident*1.6
  closed=math.sin(t*1.23+blink_phase)>.993 or (mode in ['heart','hands'] and math.sin(t*.41)>.83)
  if mode in ['seated','typing','desk_sing']:closed=False
  for side in [-1,1]:
   x=side*12
   self.line([(x-5,301,33),(x+5,301+(1 if side<0 else -1),33)],'#282c37',1.8 if closed else 2.2,True)
   if not closed:self.poly([(x-1.2,299,34),(x+1.5,299,34),(x+1.5,302,34),(x-1.2,302,34)],'#172335',False,True)
   self.line([(x-6,308,31),(x+5,310 if side<0 else 307,31)],hair,1.7,True)
  self.poly([(-3,300,34),(3,300,34),(5,285,36),(0,284,44),(-5,285,36)],blend(skin,'#e8bb9c',.12),True,True)
  self.poly([(0,284,44),(5,285,36),(-5,285,36)],blend(skin,'#593d45',.28),False,True)
  if self.glasses:
   frame='#122637'
   for side in [-1,1]:
    x=side*13
    if self.glasses=='rectangle':points=[(x-11,294,38),(x+11,294,38),(x+11,307,38),(x-11,307,38),(x-11,294,38)]
    else:points=[(x+11*math.cos(a),301+9*math.sin(a),38) for a in np.linspace(0,TAU,9)]
    self.line(points,frame,2.3 if self.glasses=='rectangle' else 1.6,True)
    self.line([(side*24,303,38),(side*32,303,21),(side*32,298,12)],frame,1.5,True)
    self.line([(x-7,306,38.5),(x-2,306,38.5)],'#81a6b6',.7,True)
   self.line([(-2,302,38),(2,302,38)],frame,2,True)
  op=(sings and mouth(t if vocal_time is None else vocal_time)) if mouth_open is None else mouth_open
  y0,y1=(272,281) if op else (275.5,277.3)
  self.poly([(-4.7,y0,31.5),(4.7,y0,31.5),(4.7,y1,31.5),(-4.7,y1,31.5)],'#322332',False,True)

 def draw_long_hair(self):
  # A parted crown, a faceted back curtain and two shoulder-length front locks.
  # All geometry follows the existing head rig, leaving the shared dance untouched.
  hair=self.c['hair'];edge=blend(hair,'#7585a0',.19)
  crown=[(-30,315,16),(-34,323,-14),(-22,337,-24),(0,344,-15),
         (23,337,-23),(34,322,-12),(30,315,16),(-4,339,16),(-4,326,26)]
  self.solid(crown,[(0,1,2,7,8),(2,3,7),(3,4,7),(4,5,6,8,7),(1,5,4,3,2)],hair,True)
  self.poly([crown[7],crown[8],crown[0],(-24,327,23)],edge,True,True)
  self.poly([crown[7],(23,331,20),crown[6],crown[8]],blend(hair,'#655979',.16),True,True)
  rings=[]
  for y,width,depth,front in [(323,33,33,1),(290,36,37,1),(251,40,38,0),(216,44,35,3),(195,36,28,-1)]:
   rings.append([(-width*math.cos(a),y-(6*math.sin(a) if y==195 else 0),front-depth*math.sin(a)) for a in np.linspace(0,math.pi,9)])
  for row in range(len(rings)-1):
   for j in range(8):
    shade=edge if j in [0,7] else blend(hair,'#706286',.07 if j%2 else .13)
    self.poly([rings[row][j],rings[row+1][j],rings[row+1][j+1],rings[row][j+1]],shade,True,True)
  for side in [-1,1]:
   # Narrow sculpted locks frame the glasses and fall below the shirt collar.
   sections=[(29,320,19,6),(34,294,18,7),(33,265,21,8),(39,231,25,9),(34,203,25,3)]
   locks=[[(side*(x-w),y,z),(side*x,y,z+5),(side*(x+w),y,z-2),(side*x,y,z-10)] for x,y,z,w in sections]
   for row in range(len(locks)-1):
    for j in range(4):
     self.poly([locks[row][j],locks[row+1][j],locks[row+1][(j+1)%4],locks[row][(j+1)%4]],edge if j==0 else hair,True,True)
   self.poly(locks[-1],hair,True,True)

# A separate edit, with subdued verses and a more expansive final chorus.
SHOTS=[
 (0,'terminal','desk','seated'),(8,'desk','desk','seated'),
 (14,'slide','portrait','walk'),(17.9,'stage','medium','heart'),
 (21.5,'coding','desk','typing'),(25,'build_success','desk','seated'),(27.4,'coding_success','desk','seated'),
 (28.4,'stage','left','hands'),(35.7,'spot','direct','heart'),
 (42.35,'portal','portrait','reach'),(46.1,'stage','low','open'),
 (CHORUSES[0][0],'stage','wide','open'),(55.85,'stage','right','reach'),(59.8,'split','duet','hands'),(63.3,'spot','direct','heart'),
 (67.7,'stage','high','walk'),(68,'digital_terminal','studio','run'),(74.42,'digital_parser','studio','jump'),
 (79.71,'digital_repair','studio','repair'),(83,'terminal_cursor','studio','head'),
 (92,'stage','low','reach'),(95.5,'stage','left','heart'),(98.3,'stage','medium','hands'),
 (CHORUSES[1][0],'stage','wide','open'),(105.1,'stage','right','rise'),(109.15,'trio','duet','open'),(112.65,'spot','direct','heart'),
 (116,'ascii_assembly','studio','open'),
 (123.5,'spot','portrait','heart'),(130.1,'stage','profile','hands'),(137.9,'portal','portrait','reach'),(142.6,'spot','direct','hands'),
 (CHORUSES[2][0],'stage','low','rise'),(150,'head_bounce','studio','head'),(156,'stage','wide','open'),(156.1,'slide','portrait','reach'),(159.65,'stage','left','point'),
 (163.0,'spot','direct','open'),(165,'montage','studio','shuffle'),(183,'desk_outro','desk','desk_sing')]
SHOT_STARTS=[s[0] for s in SHOTS]

@lru_cache(maxsize=150)
def caption(i):
 text=CUES[i]['text'];im=Image.new('RGBA',(W,160));d=ImageDraw.Draw(im)
 fontpath=os.environ.get('IDCA_FONT','/System/Library/Fonts/Avenir Next.ttc')
 size=43
 f=ImageFont.truetype(fontpath,size,index=5)
 while f.getlength(text)>1700 and size>34:size-=1;f=ImageFont.truetype(fontpath,size,index=5)
 d.text((W/2,70),text,font=f,fill='#e4eff2',anchor='mm',stroke_width=1,stroke_fill='#0b1422')
 return im

@lru_cache(maxsize=1)
def overlay():
 # A soft lower scrim gives the lyrics contrast without turning them into a card.
 im=Image.new('RGBA',(W,H));d=ImageDraw.Draw(im)
 for y in range(900,H):d.line((0,y,W,y),fill=(3,9,18,round(210*((y-900)/180)**.65)))
 return im

@lru_cache(maxsize=12)
def terminal_font(size):
 return ImageFont.truetype(os.environ.get('IDCA_MONO_FONT','/System/Library/Fonts/Menlo.ttc'),size)

def terminal_frame(t):
 im=Image.new('RGB',(W,H),'#070d18');d=ImageDraw.Draw(im)
 d.rounded_rectangle((90,80,1830,1000),radius=20,fill='#0d1522',outline='#2f4053',width=2)
 d.rounded_rectangle((90,80,1830,147),radius=20,fill='#192333')
 d.rectangle((91,116,1829,147),fill='#192333')
 for x,c in [(129,'#dd6d7b'),(161,'#d8b16d'),(193,'#69b79f')]:d.ellipse((x-9,104,x+9,122),fill=c)
 d.text((960,114),'studio — terminal',font=terminal_font(22),fill='#92a5b8',anchor='mm')
 d.text((147,185),'~/music',font=terminal_font(28),fill='#7898aa')
 command='make musical-number TITLE="I Don\'t Code Anymore"'
 count=min(len(command),max(0,int((t-.55)*24)))
 d.text((147,233),'$',font=terminal_font(33),fill='#65ddc0')
 d.text((185,233),command[:count],font=terminal_font(33),fill='#e2eaf1')
 if t<2.65 and int(t*2.5)%2==0:
  xx=185+terminal_font(33).getlength(command[:count]);d.rectangle((xx,237,xx+18,270),fill='#8ae3ca')
 lines=[
  (2.7,'[1/6] Loading lived experience ............ OK','#8fa5b8'),
  (3.1,'[2/6] Generating melody ................... OK','#8fa5b8'),
  (3.5,'[3/6] Arranging the chorus ................. OK','#8fa5b8'),
  (3.9,'[4/6] Building a world of possibilities ... OK','#8fa5b8'),
  (4.3,'[5/6] Rendering the musical number ........ OK','#8fa5b8'),
  (4.7,'[6/6] Linking sense_of_accomplishment ...','#8fa5b8'),
  (5.3,"error: missing dependency 'joy'",'#f382a0'),
  (5.9,'Build failed. 0 feelings generated.','#f382a0'),
 ]
 for i,(when,text,c) in enumerate(lines):
  if t>=when:d.text((147,322+i*58),text,font=terminal_font(31),fill=c)
 if t>=6.6:
  d.text((147,848),'$',font=terminal_font(33),fill='#65ddc0')
  if int(t*1.8)%2==0:d.rectangle((185,853,204,886),fill='#8ae3ca')
 return im

def desk_frame(t,activity='idle',screen_image=None,camera=None):
 cam=CAMS['desk'] if camera is None else camera;im=Image.new('RGB',(W,H),'#0c1322');sc=Scene(cam)
 # Quiet bedroom studio: a window, scattered city lights, a shelf and a desk.
 if activity=='sing':
  # The quiet room extends into darkness as the camera retreats, without a frame edge.
  im.paste('#111d2e',(0,0,W,H));ground,_=cam.project([(0,0,-160)])
  ImageDraw.Draw(im).rectangle((0,round(ground[0,1]*S),W,H),fill='#0b1420')
 else:
  sc.poly(plane(-1000,1000,0,650,-160),'#111d2e')
  sc.poly(floor(-1200,1200,-180,1300),'#0b1420')
 box(sc,-395,-155,170,413,-152,-138,'#223347')
 sc.poly(plane(-384,-166,181,403,-136),'#102b40')
 for x,y in [(-360,206),(-325,224),(-287,213),(-245,238),(-199,221)]:
  sc.poly(plane(x,x+23,182,y+90,-134),'#142333')
  for yy in range(193,y+82,23):sc.poly(plane(x+6,x+10,yy,yy+4,-133),'#53828b')
 sc.line([(-275,182,-132),(-275,403,-132)],'#2c4357',5)
 sc.line([(-384,292,-132),(-166,292,-132)],'#2c4357',5)
 box(sc,160,377,302,312,-154,-98,'#2b394a')
 for x,h,c in [(182,62,'#50616e'),(201,73,'#535674'),(220,53,'#426d6b'),(237,65,'#4d5268')]:box(sc,x,x+14,312,312+h,-142,-112,c)
 # Chair and seated lower body remain visible beneath the desk.
 box(sc,-214,-105,115,132,16,107,'#253247')
 box(sc,-212,-108,131,213,15,36,'#29384c')
 box(sc,-169,-154,8,116,49,66,'#172332')
 for dx,dz in [(-65,0),(65,0),(0,57),(0,-38)]:sc.line([(-162,12,60),(-162+dx,5,60+dz)],'#2c3b4b',6)
 # Desk, keyboard, trackpad, cup and monitor base.
 # Subdividing the desktop lets the hands and forearms occlude it correctly.
 sc.poly(plane(-326,352,138,151,285),'#294653',True)
 sc.poly(plane(-326,352,138,151,98),'#294653',True)
 for xx in [-326,352]:sc.poly([(xx,138,98),(xx,138,285),(xx,151,285),(xx,151,98)],'#294653',True)
 for xx in range(-326,352,57):
  for zz in range(98,285,24):sc.poly(floor(xx,min(xx+57,352),zz,min(zz+24,285),151)[::-1],'#294653',True)
 for x in [-295,317]:box(sc,x-8,x+8,0,138,118,264,'#203343')
 box(sc,-144,-20,153,158,185,231,'#597079')
 for x in range(-132,-25,13):
  for z in range(191,228,11):sc.poly(floor(x,x+8,z,z+6,159),'#91a5a9')
 box(sc,14,72,152,155,198,238,'#476371')
 box(sc,102,222,152,158,154,203,'#142633')
 box(sc,152,169,158,202,169,185,'#283e4d')
 box(sc,270,301,152,188,185,218,'#546879')
 sc.poly(floor(273,298,188,215,189),'#172b35')
 # A subtly angled screen keeps the terminal visible beside the blank stare.
 center=np.array([162.,246.,165.]);matrix=rot(0,-.24,0)
 def monitor(p):return np.asarray(p)@matrix.T+center
 bezel=[(-129,-80,0),(129,-80,0),(129,80,0),(-129,80,0)]
 sc.poly(monitor(bezel),'#1c2f40')
 screen=[(-120,-70,1),(120,-70,1),(120,70,1),(-120,70,1)]
 sc.texture(monitor(screen),terminal_frame(7.8) if screen_image is None else screen_image)
 sc.line(monitor([(-128,-79,2),(128,-79,2)]),'#354e60',2)
 human=Human(sc,t,-167,76,0,{'typing':'typing','sing':'desk_sing'}.get(activity,'seated'),t-8,cam)
 human.draw(activity=='sing')
 sc.paint(im)
 if camera is not None:return im
 # Very slow creep toward the static stare; no singing or microphone here.
 zoom=1+.025*ease(((t-21.5) if activity=='typing' else (t-8))/6)
 im=im.resize((round(W*zoom),round(H*zoom)),Image.Resampling.BILINEAR)
 xx=(im.width-W)//2;yy=(im.height-H)//2
 return im.crop((xx,yy,xx+W,yy+H))

def outro_camera(t):
 u=ease((t-183)/(DURATION-183));distance=760*math.exp(math.log(6800/760)*u)
 return Camera(position=(-70,290+230*u,distance),target=(-50,175,80),focal=1130)

def desk_outro(t):
 from digital_scenes import coding_editor
 return desk_frame(t,'sing',coding_editor(23.8),outro_camera(t))

def performance_frame(t,override=None,shot_end=None):
 si=max(0,bisect.bisect_right(SHOT_STARTS,t)-1)
 start,kind,camname,pose=SHOTS[si] if override is None else override
 u=t-start;cam=CAMS[camname];idx=bisect.bisect_right(STARTS,t)-1
 cue=CUES[idx] if idx>=0 and t<CUES[idx]['end'] else None
 sec=CUES[idx]['section'] if idx>=0 else 'Intro';chorus_id=chorus_index(t)
 # Settle at the end of the final orbit until the montage cut; lights use strict bounds.
 if CHORUSES[-1][1]<=t<166:chorus_id=len(CHORUSES)-1
 chorus=chorus_id is not None
 if chorus:
  kind='stage';cam=chorus_camera(t,chorus_id);pose='open';u=t-CHORUSES[chorus_id][0]
 palette='purple' if chorus else ('green' if sec in ['Bridge','Outro'] else 'blue')
 actualkind='stage' if kind=='stage' else ('split' if kind in ['split','trio'] else ('portal' if kind=='portal' else 'spot'))
 base=scene_background(cam,actualkind,palette) if chorus else background(camname,actualkind,palette).copy()
 im=lighting(base,cam,t,actualkind,palette)
 cast=[]
 if kind=='stage':
  # Backing singers join choruses; quiet, attentive movement during verses.
  backing_pose='dance' if dance_section(t) is not None else 'heart'
  # Leave room for both dancers to travel in the same direction at the widest gestures.
  spacing=265 if backing_pose=='dance' else 305
  cast=[(-spacing,-140,1,backing_pose,.88,chorus),(spacing,-140,2,backing_pose,.9,chorus),(0,30,0,pose,1,True)]
 elif kind in ['slide','slide_right']:
  x=(1 if kind=='slide_right' else -1)*650*(1-ease(u/1.0))
  cast=[(x,30,0,'walk' if u<1.1 else pose,1,True)]
 elif kind=='split':cast=[(-190,30,0,pose,1,True),(190,30,2,pose,1,chorus or sec=='Outro')]
 elif kind=='trio':cast=[(-285,10,1,pose,.88,chorus),(0,40,0,pose,1,True),(285,10,2,pose,.9,chorus)]
 else:cast=[(0,30,0,pose,1,True)]
 # Small contact shadows place the cast on the stage floor.
 sc=Scene(cam)
 bank,power=beat_light(t)
 if bank is not None:sc.spot=(('#48efd1','#a079ff')[bank],power)
 humans=[(Human(sc,t,x,z,ident,mode,u,cam,scale),sings) for x,z,ident,mode,scale,sings in cast]
 for human,sings in humans:
  x,_,z=human.pos;scale=human.scale
  pts=[(x+58*scale*math.cos(a),3.1,z+26*scale*math.sin(a)) for a in np.linspace(0,TAU,25)]
  sc.poly(pts,'#07101c')
 for human,sings in humans:human.draw(sings)
 sc.paint(im)
 # Gentle optical push-in within each cut; lyric placement stays fixed.
 end=shot_end if shot_end is not None else (SHOTS[si+1][0] if si+1<len(SHOTS) else DURATION)
 zoom=1 if chorus else 1+.035*ease(u/max(.1,end-start))
 im=im.resize((round(W*zoom),round(H*zoom)),Image.Resampling.BILINEAR)
 ox=(im.width-W)//2;oy=(im.height-H)//2
 im=im.crop((ox,oy,ox+W,oy+H))
 return im

def render(t,override=None):
 core=sys.modules[__name__]
 if override is not None:im=performance_frame(t,override)
 elif t>=183:im=desk_outro(t)
 elif t<14:
  im=terminal_frame(t) if t<8 else desk_frame(t)
  return Image.blend(Image.new('RGB',(W,H),'#070d18'),im,ease(t/.3)) if t<.3 else im
 elif 21.5<=t<28.4:
  from digital_scenes import render_coding
  im=render_coding(core,t)
 elif 68<=t<83:
  from digital_scenes import render_digital
  im=render_digital(core,t)
 elif 83<=t<92 or 116<=t<123.5 or 150<=t<156 or t>=165:
  from terminal_sequences import render_terminal_cursor,render_ascii,render_head_bounce,render_montage
  if t<92:im=render_terminal_cursor(core,t)
  elif t<123.5:im=render_ascii(core,t)
  elif t<156:im=render_head_bounce(core,t)
  else:im=render_montage(core,t)
 else:im=performance_frame(t)
 im=Image.alpha_composite(im.convert('RGBA'),overlay()).convert('RGB')
 idx=bisect.bisect_right(STARTS,t)-1
 if idx>=0 and t<CUES[idx]['end']:cap=caption(idx);im.paste(cap,(0,925),cap)
 fade=min(1,t/.5,(DURATION-t)/2.3)
 if fade<1:im=Image.blend(Image.new('RGB',im.size,'#030812'),im,clamp(fade))
 return im

def render_segment(start,end,dest):
 first=round(start*FPS);last=round(end*FPS)
 cmd=['ffmpeg','-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-threads','3','-movflags','+faststart',str(dest)]
 p=subprocess.Popen(cmd,stdin=subprocess.PIPE);st=time.time()
 try:
  for i in range(first,last):
   p.stdin.write(render(i/FPS).tobytes())
   if (i-first)%300==0:print(f'{dest.name}: {i-first}/{last-first} frames, {time.time()-st:.1f}s',flush=True)
 finally:p.stdin.close()
 if p.wait():raise RuntimeError('FFmpeg encode failed')
 print(f'Complete {dest.name} ({time.time()-st:.1f}s)',flush=True)

if __name__=='__main__':
 if sys.argv[1]=='segment':render_segment(float(sys.argv[2]),float(sys.argv[3]),Path(sys.argv[4]))
 elif sys.argv[1]=='stills':
  times=[2.8,23.3,37.5,44.1,52.6,57.0,61.4,80.0,111.4,128,150,180]
  sheet=Image.new('RGB',(1920,810))
  for i,t in enumerate(times):
   im=render(t);im.save(WORK/f'frame-{t:g}.jpg',quality=95)
   sheet.paste(im.resize((480,270),Image.Resampling.LANCZOS),(i%4*480,i//4*270))
  sheet.save(WORK/'contact.jpg',quality=94)

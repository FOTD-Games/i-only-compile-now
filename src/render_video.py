"""A procedural low-poly 1960 supper-club performance. Camera-space meshes; vocal-driven faces."""
from pathlib import Path
from functools import lru_cache
import os, sys, json, math, bisect, subprocess, time
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from choreography import dance_pose
from timeline import T,DURATION

ROOT=Path(__file__).resolve().parents[1]
WORK=Path(os.environ.get('IDCA_WORK_DIR',str(ROOT/'work')));WORK.mkdir(parents=True,exist_ok=True)
DATA=ROOT/'data'
W,H,S,FPS=1920,1080,1.5,30
CUES=json.loads((DATA/('cues.json' if (DATA/'cues.json').exists() else 'source-cues.json')).read_text())
STARTS=[c['start'] for c in CUES]
TRACK=np.load(DATA/'mouth-track.npz') if (DATA/'mouth-track.npz').exists() else None
BEATS=json.loads((DATA/'beats.json').read_text())['beats']
DRUM_BEATS=json.loads((DATA/'percussion-beats.json').read_text())['beats']
TAU=math.tau

def font_default(var,*paths):
 # macOS faces first (upstream), then Linux URW equivalents.
 return os.environ.get(var) or next((p for p in paths if Path(p).exists()),paths[-1])
CAPTION_FONT=font_default('IDCA_FONT','/System/Library/Fonts/Avenir Next.ttc','/usr/share/fonts/opentype/urw-base35/URWGothic-Book.otf')
CAPTION_INDEX=int(os.environ.get('IDCA_FONT_INDEX',5 if CAPTION_FONT.endswith('.ttc') else 0))
MONO_FONT=font_default('IDCA_MONO_FONT','/System/Library/Fonts/Menlo.ttc','/usr/share/fonts/opentype/urw-base35/NimbusMonoPS-Regular.otf')
# A Courier-style bold stands in for the 1403 chain printer's type.
PRINT_FONT=font_default('IDCA_PRINT_FONT','/usr/share/fonts/opentype/urw-base35/NimbusMonoPS-Bold.otf','/System/Library/Fonts/Courier.ttc')
# Two alternating chorus light banks: warm amber footlights and blue-white console lamps.
GELS=('#ffc46b','#9ec4ff')

# Explicit vocal section bounds prevent the last chorus cue leaking into a bridge/outro.
CHORUSES=[]
for i,cue in enumerate(CUES):
 if cue['section'] in ['Chorus','Final Chorus']:
  if i==0 or CUES[i-1]['section']!=cue['section']:CHORUSES.append([cue['start'],cue['end']])
  else:CHORUSES[-1][1]=cue['end']

def find_daisy():
 # Verse 2's aside: he asks "And Daisy?", she answers "Daisy," and he sings on.
 for i,c in enumerate(CUES[:-2]):
  if c['text'].lower().startswith('and daisy') and CUES[i+1].get('singer')=='backing':
   ask,ans,resume=CUES[i],CUES[i+1],CUES[i+2]
   return dict(start=ask['start']-.9,ask=ask['start'],answer=ans['start'],answer_end=ans['end'],resume=resume['start'],end=resume['end']+.35)
 return None
DAISY=find_daisy()
# Backing-only lines outside the choruses; the women lean into lead-only shots for these.
BACKING=[(c['start'],c['end']) for c in CUES if c.get('singer')=='backing' and c['section'] not in ['Chorus','Final Chorus','Coda']]

def backing_lean(t):
 return max([min(ease((t-a+.4)/.4),ease((b+.45-t)/.45)) for a,b in BACKING if a-.4<=t<b+.45],default=0)

def chorus_index(t):
 return next((i for i,(start,end) in enumerate(CHORUSES) if start<=t<end),None)

def dance_section(t):
 # Hold the final chorus entrance still; resume on the return from the head insert.
 last=len(CHORUSES)-1
 if T['chorus']['dance_hold'][0]<=t<T['chorus']['dance_hold'][1]:return last
 section=chorus_index(t)
 return section if section is not None and section<last else None

def clamp(x):return max(0,min(1,x))
def ease(x):x=clamp(x);return x*x*(3-2*x)
def color(c):return np.array(tuple(int(c[i:i+2],16) for i in (1,3,5))) if isinstance(c,str) else np.array(c)
def blend(a,b,p):return tuple(np.clip(color(a)*(1-p)+color(b)*p,0,255).astype(int))
def rot(rx=0,ry=0,rz=0):
 cx,sx=math.cos(rx),math.sin(rx);cy,sy=math.cos(ry),math.sin(ry);cz,sz=math.cos(rz),math.sin(rz)
 return np.array([[cz,-sz,0],[sz,cz,0],[0,0,1]])@np.array([[cy,0,sy],[0,1,0],[-sy,0,cy]])@np.array([[1,0,0],[0,cx,-sx],[0,sx,cx]])
def mouth(t,who=None):
 if TRACK is None or not TRACK['open'][min(len(TRACK['open'])-1,max(0,round(t*100)))]:return False
 # The vocal stem mixes every voice; the cue's singer decides whose mouth moves.
 if who is not None:
  i=bisect.bisect_right(STARTS,t)-1
  if i>=0 and t<CUES[i]['end'] and CUES[i].get('singer') not in (None,'both',who):return False
 return True
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

# Cuts flagged True snap to the nearest isolated drum attack; null means the chorus start.
def camera_cut(index,when,name,snap=False):
 return (CHORUSES[index][0] if when is None else (nearby_drum(when) if snap else when),name)
CHORUS_CAMERA_CUTS=[[camera_cut(i,*cut) for cut in cuts] for i,cuts in enumerate(T['chorus']['cameras'])]

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
   c=tuple(np.clip(color(c)*light+np.array([26,16,4])*max(0,-n[0])+np.array([6,10,26])*max(0,n[0]),0,255).astype(int))
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

# (dark, light, accent A, accent B). Keys kept from upstream: blue=verse, green=bridge/outro, purple=chorus.
PALETTES={
 'blue':('#0b1119','#2b3d55','#ffc46b','#8fb8ff'),
 'green':('#0e1411','#2e463a','#f2d38a','#86c9a9'),
 'purple':('#16090b','#5c1d22','#ffcf70','#ff9a5c'),
}
WOOD,WOOD_DARK,GOLD,CABINET='#3a2519','#24170f','#c9a45c','#8a929c'
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

TAPE_DRIVES=[-390,-200,200,390]

@lru_cache(maxsize=1)
def stand_card():
 im=Image.new('RGB',(240,330),'#5a1c22');d=ImageDraw.Draw(im)
 d.rectangle((10,10,229,319),outline=GOLD,width=5)
 d.text((120,130),'704',font=ImageFont.truetype(CAPTION_FONT,92,index=CAPTION_INDEX),fill=GOLD,anchor='mm')
 for y in [200,224]:d.line((40,y,200,y),fill=GOLD,width=3)
 return im

def scene_background(cam,kind,palette):
 dark,light,cyan,purple=PALETTES[palette];im=backdrop(palette).copy()
 sc=Scene(cam)
 if kind=='stage':
  # Pleated stage curtain behind a bandstand; four IBM 729 tape drives stand in for the band.
  for j in range(30):
   x=-1440+j*96
   sc.poly([(x,0,-445),(x+48,0,-425),(x+48,640,-425),(x,640,-445)],blend(dark,light,.48))
   sc.poly([(x+48,0,-425),(x+96,0,-445),(x+96,640,-445),(x+48,640,-425)],blend(dark,light,.16))
  # Gold-fringed valance across the top of the curtain.
  sc.poly(plane(-1500,1500,520,640,-404),blend(dark,light,.3))
  for x in range(-1500,1500,60):sc.line([(x,520,-403),(x+30,500,-403),(x+60,520,-403)],GOLD,1.6)
  # Mid-century arch and starburst frame the lead.
  arch=[(390*math.cos(a),40+430*math.sin(a),-410) for a in np.linspace(0,math.pi,25)]
  sc.line(arch,blend(dark,cyan,.45),8);sc.line(arch,GOLD,1.8)
  for k in range(12):
   a=k*TAU/12;r0,r1=(18,58) if k%2 else (18,88)
   sc.line([(r0*math.cos(a),400+r0*math.sin(a),-409),(r1*math.cos(a),400+r1*math.sin(a),-409)],cyan,2.2)
  for x in TAPE_DRIVES:
   box(sc,x-75,x+75,0,372,-420,-388,CABINET)
   sc.poly(plane(x-62,x+62,205,318,-387),'#1b2128')
   for dx in [-32,32]:
    sc.poly([(x+dx+29*math.cos(a),262+29*math.sin(a),-386) for a in np.linspace(0,TAU,17)],'#b9bec4')
    sc.poly([(x+dx+8*math.cos(a),262+8*math.sin(a),-385.5) for a in np.linspace(0,TAU,9)],'#4a525c')
   for dx in [-34,34]:
    sc.poly(plane(x+dx-18,x+dx+18,40,185,-387),'#232a33')
    sc.line([(x+dx-10,185,-386.5),(x+dx-10,95+25*math.sin(x+dx),-386.5),(x+dx+10,95+25*math.sin(x+dx),-386.5),(x+dx+10,185,-386.5)],'#5b3a22',2)
   sc.poly(plane(x-62,x+62,192,200,-387),'#3c444e')
   sc.poly(plane(x-64,x+64,340,364,-387),'#2b3138')
  sc.poly(floor(-1500,1500,-500,1100),WOOD)
  # Parquet dance floor.
  for z in range(-400,1000,70):sc.line([(-1600,0,z),(1600,0,z)],WOOD_DARK,.65)
  for x in range(-1300,1400,140):sc.line([(x,0,-450),(x,0,1000)],WOOD_DARK,.6)
  # Round bandstand risers with brass edges.
  for x,z,r in [(0,25,155),(-305,-135,112),(305,-135,112)]:
   pts=[(x+r*math.cos(a),3,z+r*.55*math.sin(a)) for a in np.linspace(0,TAU,25)]
   sc.poly(pts,'#4a2e20');sc.line(pts,GOLD,1.3)
  # Music stands with the band's monogram.
  for side in [-1,1]:
   box(sc,side*570-55,side*570+55,0,150,-255,-215,'#3d1418')
   sc.texture([(side*570-48,10,-214),(side*570+48,10,-214),(side*570+48,142,-214),(side*570-48,142,-214)],stand_card())
  # A lighting pipe with follow-spot cans.
  sc.line([(-840,545,-260),(840,545,-260)],'#2d2725',9)
  for x in [-620,-310,310,620]:
   box(sc,x-18,x+18,494,538,-269,-236,'#221d1b')
   sc.poly(plane(x-12,x+12,494,503,-234),cyan if x<0 else purple)
  # Hooded footlights along the front of the bandstand.
  for x in [-360,-180,180,360]:
   box(sc,x-24,x+24,1,22,160,196,'#2a1c14')
   sc.poly(floor(x-17,x+17,166,190,23),'#ffd98a')
 else:
  # Isolated setups: an empty light pool, side-lit portrait, or a geometric alcove.
  sc.poly(floor(-1400,1400,-1000,1200),'#120d0b')
  for j in range(3):
   r=120+j*35
   pts=[(r*math.cos(a),.5,r*.62*math.sin(a)) for a in np.linspace(0,TAU,65)]
   sc.line(pts,blend(dark,cyan,.14+j*.04),1)
  if kind=='portal':
   # A gilded proscenium arch.
   arch=[(142*math.cos(a),270+128*math.sin(a),-95) for a in np.linspace(0,math.pi,17)]
   pts=[(142,0,-95)]+arch+[(-142,0,-95)]
   sc.line(pts,blend(dark,GOLD,.4),7);sc.line(pts,GOLD,2.4)
  elif kind=='split':
   d=ImageDraw.Draw(im);d.rectangle((0,0,W//2,H),fill='#2a1215');d.rectangle((W//2,0,W,H),fill='#132033')
   d.line((W//2,0,W//2,H),fill=GOLD,width=3)
 sc.paint(im)
 return im

def light_start(section):
 # First lit drum hit per chorus; null in the timeline means the chorus start.
 when=T['chorus']['light_start'][section]
 return CHORUSES[section][0] if when is None else when

def beat_light(t):
 section=chorus_index(t)
 if section is None:return None,0
 start=max(CHORUSES[section][0],light_start(section))
 if t<start:return None,0
 i=bisect.bisect_right(DRUM_BEATS,t)-1
 if i<0:return None,0
 if DRUM_BEATS[i]<start:return None,0
 # A brisk onset and soft falloff: one colored bank fires on each measured beat.
 age=t-DRUM_BEATS[i];strength=max(0,1-age/.25)**1.4
 offset=bisect.bisect_left(DRUM_BEATS,start)
 return (i-offset)%2,strength

def tape_motion(d,cam,t):
 # Reels jerk forward and settle, as 729 drives did; console lamps twinkle or fire on the beat.
 bank,power=beat_light(t);beat=bisect.bisect_right(DRUM_BEATS,t)
 for n,x in enumerate(TAPE_DRIVES):
  for k,dx in enumerate([-32,32]):
   angle=(1 if k else -1)*(t*2.1+.9*math.sin(t*3.3+n))+n
   for j in range(3):
    a=angle+j*TAU/3
    p,z=cam.project([(x+dx+9*math.cos(a),262+9*math.sin(a),-385),(x+dx+27*math.cos(a),262+27*math.sin(a),-385)])
    if z.min()>2:d.line([(round(px*S),round(py*S)) for px,py in p],fill=(74,82,92,255),width=max(1,round(2.2*S*1000/z.mean())))
  for j in range(8):
   seed=(j*7+n*5+(beat if power>0 else int(t*3)))%5
   lit=seed<2 if power>0 else seed==0
   p,z=cam.project([(x-56+j*16,352,-386)])
   if z[0]>2:
    xx,yy=p[0]*S;r=max(1.5,5*1000/z[0])
    c=color(GELS[bank]) if (power>0 and lit) else (np.array([255,214,140]) if lit else np.array([70,60,50]))
    d.ellipse((xx-r,yy-r,xx+r,yy+r),fill=(*[int(v) for v in c],255))

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
 if kind=='stage':tape_motion(d,cam,t)
 im=Image.alpha_composite(im.convert('RGBA'),ov).convert('RGB')
 bank,power=beat_light(t)
 if power<=0:return im
 # Two independent banks, each containing ceiling downlights and floor uplights.
 gel=GELS[bank];rgb=tuple(int(v) for v in color(gel))
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

# 1960 machine-room wardrobe. For the dress, `pants` is the stocking colour below the hem.
CAST=[
 dict(skin='#cb987f',jacket='#ebe7da',pants='#2b2d33',hair='#1d1a18',shirt='#ebe7da',accent='#1f3550',outfit='shirt_tie',glasses='browline'),
 dict(skin='#946d5c',jacket='#3f6f8f',pants='#7c5a4c',hair='#181e27',shirt='#f2efe6',accent='#c9a45c',outfit='dress',glasses='cateye',gender='woman',hairstyle='long'),
 dict(skin='#dbb2a0',jacket='#c98a8f',pants='#d2a891',hair='#9a4a24',shirt='#efece4',accent='#f4efe2',skirt='#3b3f5c',outfit='twinset',glasses=None,gender='woman',hairstyle='long'),
 # The two voices that join in the coda.
 dict(skin='#e0b8a0',jacket='#7a2f3a',pants='#c99e88',hair='#6b3b22',shirt='#f2efe6',accent='#c9a45c',outfit='dress',glasses=None,gender='woman',hairstyle='long'),
 dict(skin='#6e4a3c',jacket='#2f4a3a',pants='#5c3e33',hair='#141414',shirt='#f2efe6',accent='#c9a45c',outfit='dress',glasses='cateye',gender='woman',hairstyle='long'),
]
CALM_POSES={'hymn','coy','desk_sing','seated'}

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
  self.calm=pose in CALM_POSES
  if self.calm:
   # Still poses breathe slowly instead of bouncing to the club beat.
   self.pos=np.array([x,3+.5*math.sin(t*1.1+ident),z]);self.yaw=face*.67+.015*math.sin(t*.35+ident);self.roll=.006*math.sin(t*.5+ident);self.pitch=0
  self.R=rot(self.pitch,self.yaw,self.roll)
  self.headR=rot(.045*math.sin(t*1.2)-(.075 if pose=='rise' else 0),face*.33+.06*math.sin(u*.6),-.03*sw)
  if self.calm:self.headR=rot(.02*math.sin(t*.45+ident),face*.33+.03*math.sin(t*.3+ident),-.008*math.sin(t*.4))
  if pose in ['seated','typing','desk_sing']:
   self.pos=np.array([x,-15,z]);self.R=rot(0,.53,0);self.headR=rot(.035,.30,0)
   if pose=='desk_sing':self.headR=rot(.035,-.32+.62*ease((t-T['outro']['turn'])/2),0)
  if pose in ['run','jump','repair']:
   self.pos=np.array([x,3+abs(math.sin(t*14.3))*5,z]);self.R=rot(.13,1.15,-.035);self.headR=rot(0,-.12,0)
  if pose=='dance':
   section=dance_section(t);section=0 if section is None else section
   first=bisect.bisect_left(DRUM_BEATS,light_start(section))
   # The final chorus always gets the longest routine, however many choruses the song has.
   routine=-1 if section==len(CHORUSES)-1 else section
   self.dance=dance_pose(dance_clock(t)-first,routine)
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
   step=0 if self.calm else math.sin(phase*.5+(0 if side<0 else math.pi))
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
  elif mode=='coy':
   # From hands clasped low to one hand lifted at her shoulder, the other on her hip.
   k=ease(self.u)
   handL=np.array([-9,168,52.])*(1-k)+np.array([-58,150,18.])*k;elbowL=np.array([-52,180,22.])*(1-k)+np.array([-86,186,-4.])*k
   handR=np.array([9,166,54.])*(1-k)+np.array([30,262,46.])*k;elbowR=np.array([52,180,22.])*(1-k)+np.array([70,212,30.])*k
  elif mode=='hymn':
   # Unaccompanied: hands loosely clasped low in front, no microphone.
   handL=np.array([-9,168,52.]);elbowL=np.array([-52,180,22.]);handR=np.array([9,166,54.]);elbowR=np.array([52,180,22.])
  elif mode=='repair':
   lift=ease(self.u);handR=np.array([42,103+160*lift,83.]);elbowR=np.array([62,157+42*lift,33.]);handL=np.array([-46,148+75*lift,53.]);elbowL=np.array([-62,180,15.])
  for side,elbow,hand in [(-1,elbowL,handL),(1,elbowR,handR)]:
   shoulder=np.array([side*48,225,0.]);sleeve=c['jacket']
   wrist=hand-[0,8,0];axis=wrist-elbow;axis/=np.linalg.norm(axis)
   if self.outfit=='shirt_tie':
    # Short-sleeved white shirt: the hem sits above the elbow, bare forearms below.
    hem=shoulder+(elbow-shoulder)*.58
    self.tube(shoulder,hem,18,16,sleeve);self.tube(hem,elbow,11,10,c['skin']);self.tube(elbow,wrist,10,8,c['skin'])
   else:
    self.tube(shoulder,elbow,18,13,sleeve);self.tube(elbow,wrist,13,8,sleeve)
    self.tube(wrist-axis*9,wrist,10.5,9,blend(sleeve,'#f0f3eb',.13) if self.outfit in ['dress','twinset'] else blend(sleeve,'#2a2018',.25))
   if mode in ['typing','desk_sing']:
    self.tube(hand+[0,0,-10],hand+[0,0,7],7,7,c['skin'],5)
    for j in range(4):self.tube(hand+[-5+j*3.5,0,5],hand+[-5+j*3.5,-3,17],2,1.5,c['skin'],4)
   else:self.hand(hand,'grip' if mode=='hymn' else 'palm' if mode=='coy' else 'palm' if mode=='dance' else ('grip' if side>0 else ('palm' if mode in ['open','hands','reach','rise','point','repair'] else 'grip')))
  if mode not in ['seated','typing','desk_sing','dance','run','jump','repair','hymn','coy']:
   # A chrome 1950s dynamic microphone.
   self.tube(handR+[4,-13,0],handR+[-9,22,0],3.4,4.4,'#2b2b2e',8)
   self.tube(handR+[-9,22,0],handR+[-15,40,0],8.2,7,'#cfd2d6',8)
   for dy in [26,30,34,38]:self.line([handR+[-6-dy*.37,dy,5],handR+[6-dy*.37,dy,5]],'#7d8088',.7)
  self.draw_head(sings,vocal_time)
 def draw_outfit(self):
  c=self.c
  if self.outfit=='shirt_tie':
   # White short-sleeve shirt, narrow tie, pocket protector, belt.
   for side in [-1,1]:self.poly([(side*24,236,27),(side*5,241,28),(side*2,226,33),(side*15,221,32)],blend(c['shirt'],'#ffffff',.3))
   self.poly([(-5,233,33),(5,233,33),(4,224,34),(-4,224,34)],c['accent'])
   self.poly([(-4,224,34),(4,224,34),(7,166,35),(0,158,36),(-7,166,35)],c['accent'])
   for y in [212,196,180]:self.line([(-5,y,35),(5,y-6,35)],blend(c['accent'],'#c9a45c',.4),.9)
   self.poly([(12,194,31),(34,194,31),(35,223,30),(11,223,30)],'#f4f6f2')
   self.line([(11,223,32),(12,194,32),(34,194,32),(35,223,32)],'#9aa3ab',.8)
   for x,h,col in [(16,233,'#1d1d1f'),(22,230,'#a33a30'),(28,234,'#2f5b8a')]:
    self.line([(x,212,33),(x,h,33)],col,2.2)
   self.poly([(-32,141,28),(32,141,28),(33,151,29),(-33,151,29)],'#2a1a12')
   self.poly([(-5,142,30),(5,142,30),(5,150,30),(-5,150,30)],'#c9a45c')
  elif self.outfit=='dress':
   # Shirtwaist dress: Peter Pan collar, buttoned bodice, belt and a flared skirt.
   for side in [-1,1]:self.poly([(side*2,240,30),(side*18,238,28),(side*20,229,31),(side*8,226,33)],c['shirt'])
   for y in [214,196,178,160]:self.poly([(-1.6,y-1.6,33),(1.6,y-1.6,33),(1.6,y+1.6,33),(-1.6,y+1.6,33)],c['shirt'],False)
   self.poly([(-33,146,28),(33,146,28),(33,154,29),(-33,154,29)],'#1f1d1c')
   self.poly([(-5,146,30),(5,146,30),(5,154,30),(-5,154,30)],c['accent'])
   self.skirt(c['jacket'])
  elif self.outfit=='twinset':
   # Twinset: a buttoned cardigan over a shell, a string of pearls, a full skirt.
   self.poly([(-20,238,28),(20,238,28),(0,214,32)],blend(c['jacket'],'#ffffff',.25))
   self.line([(-23,237,30),(0,206,34),(23,237,30)],blend(c['jacket'],'#5a2a30',.3),2.4)
   for k in range(11):
    a=math.pi*(.15+.7*k/10);px,py=22*math.cos(a),238-14*math.sin(a)
    self.poly([(px-1.6,py-1.6,34),(px+1.6,py-1.6,34),(px+1.6,py+1.6,34),(px-1.6,py+1.6,34)],c['accent'],False)
   for y in [196,180,164]:self.poly([(-1.8,y-1.8,33),(1.8,y-1.8,33),(1.8,y+1.8,33),(-1.8,y+1.8,33)],'#f4efe2',False)
   self.poly([(-33,146,28),(33,146,28),(33,153,29),(-33,153,29)],blend(c['skirt'],'#000000',.25))
   self.skirt(c['skirt'])
  else:
   # Cardigan over a white shirt with a bow tie.
   self.poly([(-24,237,27),(24,237,27),(0,196,32)],c['shirt'])
   for side in [-1,1]:self.poly([(side*24,237,29),(side*6,242,28),(side*2,223,33),(side*13,221,32)],blend(c['shirt'],'#ffffff',.25))
   self.line([(-27,236,30),(0,193,34),(27,236,30)],blend(c['jacket'],'#2a2018',.35),3.2)
   for side in [-1,1]:self.poly([(0,231,34),(side*13,238,34),(side*13,224,34)],c['accent'])
   self.poly([(-3,228,35),(3,228,35),(3,234,35),(-3,234,35)],blend(c['accent'],'#000000',.25))
   for y in [184,170,156]:self.poly([(-2,y-2,33),(2,y-2,33),(2,y+2,33),(-2,y+2,33)],'#d8c9a8',False)
   for x in [-20,20]:self.line([(x-10,168,32),(x+10,168,32)],blend(c['jacket'],'#2a2018',.3),1)
   self.poly([(-32,141,29),(32,141,29),(33,149,30),(-33,149,30)],blend(c['jacket'],'#2a2018',.3))
 def skirt(self,col):
  # A flared skirt from the waist to just below the knee.
  n=12;top=[(36*math.cos(a),150,26*math.sin(a)) for a in np.linspace(0,TAU,n,endpoint=False)]
  hem=[(66*math.cos(a),84,52*math.sin(a)) for a in np.linspace(0,TAU,n,endpoint=False)]
  for k in range(n):
   shade=col if k%2 else blend(col,'#0e1a24',.14)
   self.poly([top[k],top[(k+1)%n],hem[(k+1)%n],hem[k]],shade)

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
  if self.ident==2 and c.get('hairstyle')!='long':self.poly([(-25,323,21),(8,335,27),(22,318,26),(-11,307,32)],hair,True,True)
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
   frame='#2a1a12' if self.glasses=='browline' else '#3a1f2b'
   for side in [-1,1]:
    x=side*13
    if self.glasses=='browline':
     # Heavy horn-rim brow over a thin metal lower rim.
     self.line([(x-11,307,38),(x+11,307,38)],frame,4.2,True)
     points=[(x-11,307,38),(x-10,296,38),(x,294,38),(x+10,296,38),(x+11,307,38)]
     self.line(points,'#9aa3ab',1.1,True)
    else:
     # Cat-eye frames sweep up at the outer corners.
     points=[(x-side*10,306,38),(x+side*6,308,38),(x+side*13,312,38),(x+side*10,300,38),(x+side*3,295,38),(x-side*8,296,38),(x-side*11,301,38),(x-side*10,306,38)]
     self.line(points,frame,2.2,True)
    self.line([(side*24,303,38),(side*32,303,21),(side*32,298,12)],frame,1.5,True)
    self.line([(x-7,304,38.5),(x-2,304,38.5)],'#d9d2c0',.7,True)
   self.line([(-2,302,38),(2,302,38)],frame,2,True)
  if getattr(self,'daisy',False):
   # A daisy tucked above the ear: for "Daisy Bell", the first song a computer sang (IBM 7094, 1961).
   cx,cy,cz=26,322,27
   for k in range(10):
    a=k*TAU/10;tip=(cx+11*math.cos(a),cy+11*math.sin(a),cz+5)
    side=(cx+3.2*math.cos(a+1.3),cy+3.2*math.sin(a+1.3),cz+5);other=(cx+3.2*math.cos(a-1.3),cy+3.2*math.sin(a-1.3),cz+5)
    self.poly([side,tip,other],'#f6f3ea',False,True)
   self.poly([(cx+3.6*math.cos(a),cy+3.6*math.sin(a),cz+5.5) for a in np.linspace(0,TAU,9)],'#e8b32e',False,True)
  op=(sings and mouth(t if vocal_time is None else vocal_time,'lead' if self.ident==0 else 'backing')) if mouth_open is None else mouth_open
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
SHOTS=[(CHORUSES[int(when[6:])][0] if isinstance(when,str) else when,kind,cam,pose) for when,kind,cam,pose in T['shots']]
SHOT_STARTS=[s[0] for s in SHOTS]

@lru_cache(maxsize=150)
def caption(i):
 text=CUES[i]['text'];im=Image.new('RGBA',(W,160));d=ImageDraw.Draw(im)
 size=43
 f=ImageFont.truetype(CAPTION_FONT,size,index=CAPTION_INDEX)
 while f.getlength(text)>1700 and size>34:size-=1;f=ImageFont.truetype(CAPTION_FONT,size,index=CAPTION_INDEX)
 d.text((W/2,70),text,font=f,fill='#f3ead2',anchor='mm',stroke_width=1,stroke_fill='#140d08')
 return im

@lru_cache(maxsize=1)
def overlay():
 # A soft lower scrim gives the lyrics contrast without turning them into a card.
 im=Image.new('RGBA',(W,H));d=ImageDraw.Draw(im)
 for y in range(900,H):d.line((0,y,W,y),fill=(12,8,5,round(210*((y-900)/180)**.65)))
 return im

@lru_cache(maxsize=12)
def terminal_font(size):
 return ImageFont.truetype(MONO_FONT,size)

@lru_cache(maxsize=12)
def print_font(size):
 return ImageFont.truetype(PRINT_FONT,size)

INK='#262321';RED_INK='#9a2a25'

@lru_cache(maxsize=2)
def greenbar(top=0):
 """Continuous-form 1403 listing paper: green bars, tractor holes, perforation."""
 im=Image.new('RGB',(W,H),'#17120f');d=ImageDraw.Draw(im)
 d.rectangle((150,0,1770,H),fill='#f1eddc')
 for y in range(top-116,H,116):d.rectangle((228,y,1692,y+58),fill='#d6e6cf')
 for x in [150,1692]:d.rectangle((x,0,x+78,H),fill='#ece7d4')
 for y in range(top%58-58,H,58):
  for x in [189,1731]:d.ellipse((x-11,y+18,x+11,y+40),fill='#17120f')
 for x in [228,1692]:
  for y in range(0,H,14):d.line((x,y,x,y+7),fill='#c4bea8',width=2)
 return im

def terminal_frame(t):
 # The opening job: a job card keypunched at the top, then the compile listing prints.
 im=greenbar().copy();d=ImageDraw.Draw(im)
 d.text((262,70),'IBM 704   FORTRAN II   MONITOR          RUN 0412          PAGE 001',font=print_font(24),fill='#6f6a5f')
 command="* MUSICAL NUMBER   'I ONLY COMPILE NOW'"
 count=min(len(command),max(0,int((t-.55)*24)))
 d.text((262,160),command[:count],font=print_font(36),fill=INK)
 if t<2.65 and int(t*2.5)%2==0:
  xx=262+print_font(36).getlength(command[:count]);d.rectangle((xx,166,xx+20,200),fill=INK)
 lines=[
  (2.7,'PASS 1  READ SOURCE DECK ................ 412 CARDS',INK),
  (3.1,'PASS 2  ARRANGE THE CHORUS ............... OK',INK),
  (3.5,'PASS 3  ASSIGN INDEX REGISTERS ........... OK',INK),
  (3.9,'PASS 4  OPTIMIZE THE MUSICAL NUMBER ...... OK',INK),
  (4.3,'PASS 5  PUNCH OBJECT DECK ................ OK',INK),
  (4.7,'PASS 6  LINK SENSE OF ACCOMPLISHMENT ....',INK),
  (5.3,'***** ERROR 07 *****   JOY NOT DEFINED',RED_INK),
  (5.9,'JOB ABANDONED.   0 FEELINGS PUNCHED.',RED_INK),
 ]
 for i,(when,text,c) in enumerate(lines):
  if t>=when:d.text((262,262+i*58),text,font=print_font(33),fill=c)
 if t>=6.6:
  d.text((262,784),'END OF JOB',font=print_font(33),fill=INK)
  if int(t*1.8)%2==0:d.rectangle((262,838,282,872),fill=INK)
 return im

def desk_frame(t,activity='idle',screen_image=None,camera=None):
 cam=CAMS['desk'] if camera is None else camera;im=Image.new('RGB',(W,H),'#16110e');sc=Scene(cam)
 # A 1960 programming office at night: window, card cabinet, desk, keypunch keyboard, listing.
 if activity=='sing':
  # The quiet room extends into darkness as the camera retreats, without a frame edge.
  im.paste('#1f1a17',(0,0,W,H));ground,_=cam.project([(0,0,-160)])
  ImageDraw.Draw(im).rectangle((0,round(ground[0,1]*S),W,H),fill='#16110e')
 else:
  sc.poly(plane(-1000,1000,0,650,-160),'#1f1a17')
  sc.poly(floor(-1200,1200,-180,1300),'#16110e')
 box(sc,-395,-155,170,413,-152,-138,'#3a2a20')
 sc.poly(plane(-384,-166,181,403,-136),'#152238')
 for x,y in [(-360,206),(-325,224),(-287,213),(-245,238),(-199,221)]:
  sc.poly(plane(x,x+23,182,y+90,-134),'#1b2a40')
  for yy in range(193,y+82,23):sc.poly(plane(x+6,x+10,yy,yy+4,-133),'#e3c27a')
 sc.line([(-275,182,-132),(-275,403,-132)],'#4a3628',5)
 sc.line([(-384,292,-132),(-166,292,-132)],'#4a3628',5)
 box(sc,160,377,302,312,-154,-98,'#4a3628')
 # Card trays and FORTRAN manuals on the shelf.
 for x,w,h,c in [(176,40,30,'#d9cfb4'),(222,40,30,'#d9cfb4'),(276,12,70,'#2f4f7a'),(291,12,62,'#7a2f2f'),(306,12,74,'#2f4f7a')]:box(sc,x,x+w,312,312+h,-142,-108,c)
 # Chair and seated lower body remain visible beneath the desk.
 box(sc,-214,-105,115,132,16,107,'#253247')
 box(sc,-212,-108,131,213,15,36,'#29384c')
 box(sc,-169,-154,8,116,49,66,'#172332')
 for dx,dz in [(-65,0),(65,0),(0,57),(0,-38)]:sc.line([(-162,12,60),(-162+dx,5,60+dz)],'#2c3b4b',6)
 # Desk, keyboard, card stack, cup and copy-holder stand.
 # Subdividing the desktop lets the hands and forearms occlude it correctly.
 sc.poly(plane(-326,352,138,151,285),'#5a3d2b',True)
 sc.poly(plane(-326,352,138,151,98),'#5a3d2b',True)
 for xx in [-326,352]:sc.poly([(xx,138,98),(xx,138,285),(xx,151,285),(xx,151,98)],'#5a3d2b',True)
 for xx in range(-326,352,57):
  for zz in range(98,285,24):sc.poly(floor(xx,min(xx+57,352),zz,min(zz+24,285),151)[::-1],'#5a3d2b',True)
 for x in [-295,317]:box(sc,x-8,x+8,0,138,118,264,'#3a281c')
 # IBM 026-style keypunch keyboard, a stack of blank cards, a coffee cup.
 box(sc,-150,-14,151,162,182,234,'#7d8792')
 for x in range(-138,-25,13):
  for z in range(189,229,11):sc.poly(floor(x,x+8,z,z+6,163),'#e6dcc2')
 box(sc,10,78,152,160,196,236,'#ece3c8')
 sc.poly(floor(14,30,198,206,160.5),'#c9b98f')
 box(sc,102,222,152,156,154,203,'#3a2a20')
 box(sc,152,169,156,202,169,185,'#3a2a20')
 box(sc,270,301,152,188,185,218,'#e9e3d3')
 sc.poly(floor(273,298,188,215,189),'#3b2414')
 # A listing clipped to a copy holder, angled toward him, replaces the monitor.
 center=np.array([162.,246.,165.]);matrix=rot(0,-.24,0)
 def monitor(p):return np.asarray(p)@matrix.T+center
 bezel=[(-129,-80,0),(129,-80,0),(129,80,0),(-129,80,0)]
 sc.poly(monitor(bezel),'#4a3426')
 screen=[(-120,-70,1),(120,-70,1),(120,70,1),(-120,70,1)]
 sc.texture(monitor(screen),terminal_frame(7.6) if screen_image is None else screen_image)
 sc.line(monitor([(-40,79,2),(40,79,2)]),'#b9bec4',5)
 human=Human(sc,t,-167,76,0,{'typing':'typing','sing':'desk_sing'}.get(activity,'seated'),t-T['intro']['desk'],cam)
 human.draw(activity=='sing')
 sc.paint(im)
 if camera is not None:return im
 # Very slow creep toward the static stare; no singing or microphone here.
 zoom=1+.025*ease(((t-T['coding']['start']) if activity=='typing' else (t-T['intro']['desk']))/6)
 im=im.resize((round(W*zoom),round(H*zoom)),Image.Resampling.BILINEAR)
 xx=(im.width-W)//2;yy=(im.height-H)//2
 return im.crop((xx,yy,xx+W,yy+H))

CODA=T.get('coda')
OUTRO_END=CODA['start'] if CODA else DURATION

def outro_camera(t):
 u=ease((t-T['outro']['start'])/(OUTRO_END-T['outro']['start']));distance=760*math.exp(math.log(6800/760)*u)
 return Camera(position=(-70,290+230*u,distance),target=(-50,175,80),focal=1130)

def desk_outro(t):
 from digital_scenes import coding_editor
 return desk_frame(t,'sing',coding_editor(T['coding']['start']+2.3),outro_camera(t))

def daisy_frame(t):
 # Two-shot on the supper-club stage: he turns to her, she answers coyly, he turns back.
 D=DAISY;u=(t-D['start'])/max(.1,D['end']-D['start'])
 cam=Camera(position=(30-40*u,268,720-60*u),target=(15,215,-15),focal=1160)
 im=lighting(scene_background(cam,'stage','blue'),cam,t,'stage','blue')
 sc=Scene(cam)
 look=ease((t-D['ask']+.5)/.4)*(1-ease((t-D['resume']+.15)/.5))
 coy=ease((t-D['answer']+.3)/.3)*(1-ease((t-D['answer_end']-.25)/.6))
 lead=Human(sc,t,-125,30,0,'open',t-D['start'],cam)
 lead.yaw+=.95*look;lead.R=rot(lead.pitch,lead.yaw,lead.roll)
 lead.headR=rot(.03*math.sin(t*1.2),-.05+.45*look,-.02*look)
 her=Human(sc,t,150,-15,1,'coy',coy,cam,.9)
 her.yaw-=.35+.25*coy;her.R=rot(her.pitch,her.yaw,her.roll+.05*coy)
 her.headR=rot(.07*coy,-.25-.25*coy+.35*coy*coy,.16*coy)
 for h in [lead,her]:
  x,_,z=h.pos;pts=[(x+58*h.scale*math.cos(a),3.1,z+26*h.scale*math.sin(a)) for a in np.linspace(0,TAU,25)];sc.poly(pts,'#07101c')
 lead.draw(True);her.draw(True);sc.paint(im)
 return im

def coda_frame(t):
 # After the music stops: one woman alone in a spotlight, then two more voices join late.
 # No period grade here; the frame is meant to break.
 push=ease((t-CODA['start'])/max(1,DURATION-CODA['start']))
 cam=Camera(position=(0,265-25*push,900-170*push),target=(0,205,0),focal=1150)
 im=Image.new('RGB',(W,H),'#060606')
 for j,(x,z,ident) in enumerate([(0,20,1),(-235,-40,2),(235,-40,3)]):
  entry=CODA['entries'][j];p=ease((t-entry+1.2)/2.2)
  if p<=0:continue
  layer=Image.new('RGBA',(W,H));d=ImageDraw.Draw(layer)
  top,_=cam.project([(x,640,z)]);pool,_=cam.project([(x+95*math.cos(a),1,z+45*math.sin(a)) for a in np.linspace(0,TAU,33)])
  ys=[q[1] for q in pool];xs=[q[0] for q in pool]
  d.polygon([(top[0,0]*S-30,top[0,1]*S),(top[0,0]*S+30,top[0,1]*S),(max(xs)*S,np.mean(ys)*S),(min(xs)*S,np.mean(ys)*S)],fill=(236,232,224,round(20*p)))
  d.polygon([(a*S,b*S) for a,b in pool],fill=(236,232,224,round(46*p)))
  sc=Scene(cam);human=Human(sc,t,x,z,ident,'hymn',t-entry,cam,.92 if j else 1);human.daisy=True
  human.draw(t>=entry);sc.paint(layer)
  im=Image.alpha_composite(im.convert('RGBA'),Image.blend(Image.new('RGBA',(W,H)),layer,p)).convert('RGB')
 return im

def performance_frame(t,override=None,shot_end=None):
 si=max(0,bisect.bisect_right(SHOT_STARTS,t)-1)
 start,kind,camname,pose=SHOTS[si] if override is None else override
 u=t-start;cam=CAMS[camname];idx=bisect.bisect_right(STARTS,t)-1
 cue=CUES[idx] if idx>=0 and t<CUES[idx]['end'] else None
 sec=CUES[idx]['section'] if idx>=0 else 'Intro';chorus_id=chorus_index(t)
 # Settle at the end of the final orbit until the montage cut; lights use strict bounds.
 if CHORUSES[-1][1]<=t<T['chorus']['settle_end']:chorus_id=len(CHORUSES)-1
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
 if bank is not None:sc.spot=(GELS[bank],power)
 humans=[(Human(sc,t,x,z,ident,mode,u,cam,scale),sings) for x,z,ident,mode,scale,sings in cast]
 lean=backing_lean(t)
 if lean>0 and kind not in ['stage','trio','split']:
  # They slide in from the frame edges and lean toward him for their answer, then ease back out.
  for side,ident in [(-1,1),(1,2)]:
   z=60;edge=640/cam.f*(cam.pos[2]-z)
   h=Human(sc,t,side*(edge*.9+(1-lean)*190),z,ident,'hymn',u,cam,.95)
   h.yaw-=side*.55*lean;h.roll=side*.2*lean;h.R=rot(h.pitch,h.yaw,h.roll)
   h.headR=rot(.03,-side*.35*lean,side*.1*lean)
   humans.append((h,True))
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

GRADE=os.environ.get('IDCA_GRADE','1')!='0'

@lru_cache(maxsize=1)
def grade_maps():
 yy,xx=np.mgrid[0:H,0:W].astype(np.float32);r=np.sqrt(((xx-W/2)/(W/2))**2+((yy-H/2)/(H/2))**2)
 vignette=np.clip(1-.28*np.clip(r-.55,0,None)**1.6,0,1)[...,None]
 rng=np.random.default_rng(1960)
 grain=[rng.normal(0,5.5,(H//2,W//2,1)).astype(np.float32).repeat(2,0).repeat(2,1) for _ in range(6)]
 return vignette,grain

def film_grade(im,t):
 # Warm early-colour film: lifted blacks, softened highlights, vignette and moving grain.
 vignette,grain=grade_maps()
 a=np.asarray(im,dtype=np.float32)
 a=a*np.array([1.05,1.0,.9],np.float32)+np.array([10,7,3],np.float32)
 a=255*(1-np.exp(-a/220))/(1-math.exp(-255/220))
 a=a*vignette+grain[int(t*24)%len(grain)]
 return Image.fromarray(np.clip(a,0,255).astype(np.uint8))

def supersampled(fn,t,k=2):
 # Slow camera moves on a tiny subject make whole-pixel vertices crawl; render big, scale down.
 global W,H,S
 saved=W,H,S;W,H,S=W*k,H*k,S*k
 try:im=fn(t)
 finally:W,H,S=saved
 return im.resize((W,H),Image.Resampling.LANCZOS)

def render(t,override=None):
 core=sys.modules[__name__]
 if override is not None:im=performance_frame(t,override)
 elif CODA and t>=CODA['start']:im=supersampled(coda_frame,t)
 elif DAISY and DAISY['start']<=t<DAISY['end']:im=daisy_frame(t)
 elif t>=T['outro']['start']:im=supersampled(desk_outro,t)
 elif t<T['intro']['perform']:
  # The listing's print timing was written for a 7.8 s opening; compress it to fit a shorter intro.
  im=terminal_frame(t*min(1,7.8/T['intro']['desk'])) if t<T['intro']['desk'] else desk_frame(t)
  if GRADE:im=film_grade(im,t)
  return Image.blend(Image.new('RGB',(W,H),'#0d0a08'),im,ease(t/.3)) if t<.3 else im
 elif T['coding']['start']<=t<T['coding']['end']:
  from digital_scenes import render_coding
  im=render_coding(core,t)
 elif T['digital']['cuts'][0][0]<=t<T['digital']['end']:
  from digital_scenes import render_digital
  im=render_digital(core,t)
 elif any(T[k]['start']<=t<T[k]['end'] for k in ['cursor','ascii','bounce','montage']):
  from terminal_sequences import render_terminal_cursor,render_ascii,render_head_bounce,render_montage
  if t<T['cursor']['end']:im=render_terminal_cursor(core,t)
  elif t<T['ascii']['end']:im=render_ascii(core,t)
  elif t<T['bounce']['end']:im=render_head_bounce(core,t)
  else:im=render_montage(core,t)
 else:im=performance_frame(t)
 if GRADE and not (CODA and t>=CODA['start']):im=film_grade(im,t)
 im=Image.alpha_composite(im.convert('RGBA'),overlay()).convert('RGB')
 idx=bisect.bisect_right(STARTS,t)-1
 if idx>=0 and t<CUES[idx]['end']:cap=caption(idx);im.paste(cap,(0,925),cap)
 fade=min(1,t/.5,(DURATION-t)/2.3)
 # The band stops: the desk fades to black before the coda.
 if CODA and T['outro']['start']<=t<CODA['start']:fade=min(fade,(CODA['start']-t)/1.5)
 if fade<1:im=Image.blend(Image.new('RGB',im.size,'#0d0a08'),im,clamp(fade))
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

STILL_TIMES=[5.8,10,23.3,25.8,37.5,52.6,57.0,61.4,70,76,80.0,86,111.4,119,128,153,168,175,186,196]

if __name__=='__main__':
 if sys.argv[1]=='segment':render_segment(float(sys.argv[2]),float(sys.argv[3]),Path(sys.argv[4]))
 elif sys.argv[1]=='stills':
  times=STILL_TIMES
  sheet=Image.new('RGB',(1920,270*((len(times)+3)//4)))
  for i,t in enumerate(times):
   im=render(t);im.save(WORK/f'frame-{t:g}.jpg',quality=95)
   sheet.paste(im.resize((480,270),Image.Resampling.LANCZOS),(i%4*480,i//4*270))
  sheet.save(WORK/'contact.jpg',quality=94)

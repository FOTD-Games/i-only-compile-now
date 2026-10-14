"""Printer-head cursor, punch-hole assembly, beat-driven card hops and the final edit."""
from functools import lru_cache
import bisect
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from timeline import T
from digital_scenes import W,H,INK,CYAN,PINK,PURPLE,mono,ease,window,syntax,token


@lru_cache(maxsize=4)
def head_image(core,opened,digital=True):
 """Use the lead's actual head mesh, including the same two mouth states."""
 class View:
  pos=np.array([0.,290.,1000.])
  def project(self,points):
   a=np.asarray(points)
   return np.stack([640+2.4*a[:,0],335-2.4*(a[:,1]-300)],axis=1),1000-a[:,2]
 view=View();layer=Image.new('RGBA',(W,H));sc=core.Scene(view)
 guy=core.Human(sc,0,0,0,0,'heart',0,view)
 guy.pos=np.zeros(3);guy.R=core.rot();guy.headR=core.rot(0,-.12,0)
 if digital:guy.c={**guy.c,'skin':'#f0c27a','hair':'#4a2a12'}
 guy.draw_head(mouth_open=opened);sc.paint(layer)
 box=layer.getbbox();return layer.crop((box[0]-8,box[1]-8,box[2]+8,box[3]+8))


def head(core,im,vocal_time,x,y,size=100,tilt=0,digital=True,alpha=255):
 sprite=head_image(core,core.mouth(vocal_time),digital)
 sprite=sprite.resize((round(sprite.width*size/sprite.height),round(size)),Image.Resampling.LANCZOS)
 if tilt:sprite=sprite.rotate(tilt,Image.Resampling.BICUBIC,expand=True)
 if alpha<255:sprite.putalpha(sprite.getchannel('A').point(lambda a:round(a*alpha/255)))
 im.paste(sprite,(round(x-sprite.width/2),round(y-sprite.height/2)),sprite)


@lru_cache(maxsize=4)
def terminal_base(title):
 im=Image.new('RGB',(W,H),'#0d0b09');d=ImageDraw.Draw(im)
 window(d,(88,69,1832,922),title)
 d.line((89,862,1831,862),fill='#3a2c1c',width=2)
 return im


def output_line(n):
 decks=['PAYROLL','ORBIT','MEMORY','LOGIC','TABLES','JOY','HANDS','FRONTIER']
 name=decks[n%len(decks)]
 choices=[
  f'COMPILE  {name:<10} STATEMENTS {112+n*13:05d}   PUNCHED',
  f'OBJECT   DECK {(n*7919)%32768:05o}         {14+n%73:02d} CARDS READY',
  f'READ     {name:<10} CHANGE DETECTED   RECOMPILING',
  f'LINK     CORE {(n*127)%32768:05o}         ADDRESSES ASSIGNED',
  f'TEST     CASE {n%24+1:02d}/24          PASS   ({8+n%17} SEC)',
  f'TRACE    REQUEST {n:04d}           ANSWER GENERATED',
  f'PRINT    LINE {n*144:06d}          LISTING COMPLETE',
  f'TAPE 3   {n*314:07d} WORDS      WAITING FOR NEXT DECK',
 ]
 return choices[n%8]


CURSOR_TIME_SCALE=.5

def render_terminal_cursor(core,t,start=None,vocal_time=None):
 start=T['cursor']['start'] if start is None else start
 vocal_time=t if vocal_time is None else vocal_time;u=(t-start)*CURSOR_TIME_SCALE
 im=terminal_base('1403 PRINTER  -  LIVE OUTPUT').copy();d=ImageDraw.Draw(im)
 # Output scrolls continuously; the active head follows the newest typed character.
 speed=3.8;position=u*speed+220;line=int(position);q=position-line
 clip=Image.new('RGBA',(1640,626));cd=ImageDraw.Draw(clip)
 for j in range(15):
  n=line-14+j;y=16+j*47-q*47
  cd.text((2,y),output_line(n),font=mono(30),fill=CYAN if n%5==0 else (PURPLE if n%3==0 else '#b59a74'))
 im.paste(clip,(148,137),clip)
 d=ImageDraw.Draw(im);s=output_line(line+1);chars=min(len(s),int(q*len(s)))
 d.rectangle((135,760,1782,855),fill='#241a0e')
 d.text((150,790),s[:chars],font=mono(31),fill='#ffe2a8')
 cursor_x=150+mono(31).getlength(s[:chars])+49
 d.line((cursor_x-24,842,cursor_x+24,842),fill=CYAN,width=3)
 head(core,im,vocal_time,cursor_x,794,99,3*math.sin(u*2.2))
 d.text((147,878),f'LINE {line+1:05d}   -   PRINTING',font=mono(23),fill='#b59a74')
 d.text((1453,878),'BCD  -  RUNNING',font=mono(22),fill=CYAN)
 return im


@lru_cache(maxsize=2)
def ascii_figure(core,opened):
 """Sample the shared human mesh into coloured Hollerith punch holes."""
 class View:
  pos=np.array([0.,230.,1000.])
  def project(self,points):
   a=np.asarray(points)
   return np.stack([640+1.7*a[:,0],548-1.29*a[:,1]],axis=1),1000-a[:,2]
 class Figure(core.Human):
  def draw_head(self,sings=True,vocal_time=None):super().draw_head(mouth_open=opened)
 view=View();sc=core.Scene(view);raw=Image.new('RGBA',(W,H))
 guy=Figure(sc,0,0,0,0,'open',1.2,view)
 guy.pos=np.zeros(3);guy.R=core.rot(0,-.08,0);guy.headR=core.rot(0,.08,0)
 guy.c={**guy.c,'skin':'#f0c27a','jacket':'#e9d8b0','pants':'#8a5a2b','hair':'#6b4320','shirt':'#e9d8b0','accent':'#9a5b2a'}
 guy.draw();sc.paint(raw)
 arr=np.asarray(raw);result=Image.new('RGBA',(W,H));d=ImageDraw.Draw(result)
 xmin,ymin,xmax,ymax=raw.getbbox();cw,ch=12,18
 for y in range(ymin//ch*ch,ymax,ch):
  for x in range(xmin//cw*cw,xmax,cw):
   patch=arr[y:y+ch,x:x+cw];mask=patch[:,:,3]>100
   if mask.mean()<.25:continue
   rgb=patch[:,:,:3][mask].mean(axis=0)
   # Dark features stay negative space, so eyes and the square mouth remain legible.
   center=arr[min(H-1,y+ch//2),min(W-1,x+cw//2),:3]
   if np.max(center)<53:continue
   # One rectangular punch per cell, the shape of an IBM card hole.
   fill=tuple(np.clip(rgb*1.15+10,0,255).astype(int))
   d.rounded_rectangle((x+2,y+2,x+cw-3,y+ch-3),radius=1,fill=fill)
 # Keep the same face readable within the glyph silhouette, at ASCII resolution.
 for x in [930,990]:
  d.rectangle((x-12,231,x+12,253),fill=(0,0,0,0))
  d.rectangle((x-8,237,x+8,241),fill='#d9a441')
 d.rectangle((945,277,975,301),fill=(0,0,0,0))
 (d.rectangle((951,278,969,296),outline='#d9a441',width=3) if opened else d.rectangle((950,286,970,290),fill='#d9a441'))
 return result


@lru_cache(maxsize=2)
def ascii_tiles(core,opened):
 im=ascii_figure(core,opened);tiles=[];cw,ch=72,36
 box=im.getbbox()
 for y in range(box[1]//ch*ch,box[3],ch):
  for x in range(box[0]//cw*cw,box[2],cw):
   tile=im.crop((x,y,x+cw,y+ch))
   if tile.getbbox():tiles.append((x,y,tile))
 return tiles


def render_ascii(core,t,start=None,vocal_time=None):
 start=T['ascii']['start'] if start is None else start
 vocal_time=t if vocal_time is None else vocal_time;u=t-start
 im=terminal_base('CARD READER  -  ASSEMBLE PERFORMER').copy();d=ImageDraw.Draw(im)
 d.text((147,151),'* ASSEMBLE SINGER FROM HOLLERITH CARDS',font=mono(25),fill=CYAN)
 stages=['READ   VOICE DECK','READ   HANDS DECK','LINK   MEMORY DECK','PUNCH  HUMAN']
 for i,s in enumerate(stages):
  if u>.35+i*.8:d.text((147,226+i*44),s,font=mono(23),fill='#b59a74' if i<3 else PURPLE)
 opened=core.mouth(vocal_time)
 if u>=5.7:
  fig=ascii_figure(core,opened);im.paste(fig,(0,0),fig)
 else:
  # Glyph blocks converge from alternating edges, compiling feet through face.
  for x,y,tile in ascii_tiles(core,opened):
   rank=(828-y)/690+((x//72)%4)*.026
   p=ease((u-.2-rank*4.65)/.7)
   if p<=0:continue
   side=-1 if (x//72+y//36)%2 else 1
   px=x+side*(1-p)*1150;py=y+(1-p)*100*math.sin(x+y)
   im.paste(tile,(round(px),round(py)),tile)
 # Source bytes keep arriving while the body is assembled in the terminal.
 d=ImageDraw.Draw(im)
 for j in range(11):
  y=206+j*53;x=1515+24*math.sin(u+j)
  s=['12-0-1-8','11-3-8-4','0-1-4-8'][j%3]
  d.text((x,y),s,font=mono(24),fill='#5b4526' if u<5.5 else '#4a3820')
 progress=min(1,max(0,u/5.7));d.rectangle((148,889,688,895),fill='#3a2c1c')
 d.rectangle((148,889,148+540*progress,895),fill=CYAN)
 d.text((730,875),f'{round(progress*100):3d}%  '+('PERFORMER ASSEMBLED' if progress==1 else 'READING CARDS'),font=mono(22),fill=CYAN)
 return im


BOUNCE_POINTS=[(345,673),(655,505),(1000,690),(1435,510),(1570,737),(1200,410),(853,511),(500,752)]
BOUNCE_LABELS=['DO','GO TO','IF','CALL','JOY','CARE','CONTINUE','END']


@lru_cache(maxsize=1)
def bounce_events(core):
 # Nearest output frame limits audio-to-animation error to half a 30 fps frame.
 return tuple(sorted(set(round(b*core.FPS)/core.FPS for b in core.DRUM_BEATS)))


def bounce_state(core,t,clip_start=None):
 clip_start=T['bounce']['start'] if clip_start is None else clip_start
 events=bounce_events(core);i=bisect.bisect_right(events,t+1e-8)-1
 if i<0:return 0,1,float('inf')
 age=max(0,t-events[i])
 if events[i]+1e-8<clip_start:return i,1,float('inf')
 # One short, triggered hop, then a complete hold until another real drum attack.
 return i,min(1,age/.22),age


def render_head_bounce(core,t,start=None,vocal_time=None):
 start=T['bounce']['start'] if start is None else start
 vocal_time=t if vocal_time is None else vocal_time;u=t-start
 im=terminal_base('REMEMBER  -  LIVE EXECUTION').copy();d=ImageDraw.Draw(im)
 lines=['FUNCTION REMEMBER(SOURCE)','JOY = BUILD(0)','DO 50 L = 1, N','IF (BROKEN(L)) 40, 50, 50','40 CALL REPAIR(L)','CARE = CARE + EFFORT','50 CONTINUE','REMEMBER = JOY','RETURN','END']
 # Dense editor text gives each jump a place within the code, beneath the bright words.
 for column in range(3):
  for j in range(13):
   y=152+j*52;line=lines[(j+column*3)%len(lines)]
   d.text((145+column*552,y),f'{column*13+j+1:02d}',font=mono(20),fill='#4a3820')
   d.text((192+column*552,y),line,font=mono(22),fill='#5b4526' if j%3 else '#4a4a5a')
 # Use measured audio onsets, including during the later montage reprise.
 i,q,age=bounce_state(core,vocal_time,vocal_time-u)
 active=(i-1)%len(BOUNCE_POINTS);nxt=i%len(BOUNCE_POINTS)
 for j,((x,y),label) in enumerate(zip(BOUNCE_POINTS,BOUNCE_LABELS)):
  color=CYAN if j==active and age<.12 else ('#9ec4ff' if j%2 else '#d0a060')
  token(im,label,x,y+52,0,35,color)
 a=np.array(BOUNCE_POINTS[active]);b=np.array(BOUNCE_POINTS[nxt])
 def point(f):
  p=a*(1-f)+b*f;return p[0],p[1]-48-145*math.sin(math.pi*f)
 # Faint previous positions show the bouncing path, with a brief impact ring.
 for back,alpha in [(.22,35),(.12,65)]:
  if back<=q<1:
   x,y=point(q-back);head(core,im,vocal_time,x,y,128,0,True,alpha)
 x,y=point(q);head(core,im,vocal_time,x,y,140*(1+.08*max(0,1-age/.07)),13*math.sin(math.pi*q)*(1 if i%2 else -1))
 if age<.12:
  d=ImageDraw.Draw(im);r=55+age*230
  d.ellipse((a[0]-r,a[1]+17-age*20,a[0]+r,a[1]+33+age*20),outline=CYAN,width=3)
 d=ImageDraw.Draw(im);d.text((150,878),'EXECUTION   -   STEP / JUMP / RETURN',font=mono(23),fill='#b59a74')
 return im


@lru_cache(maxsize=1)
def montage_cuts(core):
 """Directed opening of the montage, followed by the existing closing cuts."""
 cuts=T['montage']['cuts'];ends=[c[0] for c in cuts[1:]]+[T['montage']['end']]
 return [dict(start=a,end=b,scene=scene) for (a,scene),b in zip(cuts,ends)]


def render_montage(core,t):
 from digital_scenes import render_coding,render_digital
 cut=next(c for c in montage_cuts(core) if c['start']<=t<c['end'])
 start,end,scene=cut['start'],cut['end'],cut['scene'];u=t-start
 if scene=='singer_close':return core.performance_frame(t,(start,'spot','portrait','hands'),end)
 if scene.startswith('stage_'):
  kind,cam,pose={'stage_wide':('stage','wide','open'),'stage_profile':('stage','profile','hands'),'stage_split':('split','duet','hands'),'stage_low':('stage','low','rise')}[scene]
  return core.performance_frame(t,(start,kind,cam,pose),end)
 if scene=='cursor':return render_terminal_cursor(core,T['cursor']['start']+u,vocal_time=t)
 if scene=='ascii':return render_ascii(core,T['ascii']['start']+u/(end-start)*6.9,vocal_time=t)
 if scene=='bounce':return render_head_bounce(core,T['bounce']['start']+u,vocal_time=t)
 if scene=='parser':return render_digital(core,T['digital']['cuts'][1][0]+u*.85,vocal_time=t)
 if scene=='repair':return render_digital(core,T['digital']['cuts'][2][0]+u/(end-start)*3.25,vocal_time=t)
 if scene=='typing':return render_coding(core,T['coding']['start']+min(3.3,u))
 if scene=='success':return render_coding(core,T['coding']['success']+min(2.2,u*1.7))
 raise ValueError(scene)

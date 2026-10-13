"""Terminal-head cursor, ASCII assembly, beat-driven code hops and the final edit."""
from functools import lru_cache
import bisect
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
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
 if digital:guy.c={**guy.c,'skin':'#78d9c9','hair':'#4b5c99'}
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
 im=Image.new('RGB',(W,H),'#070e1c');d=ImageDraw.Draw(im)
 window(d,(88,69,1832,922),title)
 d.line((89,862,1831,862),fill='#243e54',width=2)
 return im


def output_line(n):
 modules=['screen.tsx','parser.ts','memory.ts','logic.ts','routes.ts','joy.ts','hands.ts','frontier.ts']
 name=modules[n%len(modules)]
 choices=[
  f'[compile] {name:<16}  tokens={112+n*13:05d}  -> linked',
  f'[emit]    chunk.{(n*7919)%65536:04x}.js          {14+n%73:02d} modules ready',
  f'[watch]   src/{name:<16}  change detected; rebuilding...',
  f'[resolve] graph:{n*127:06d}           dependencies -> optimized',
  f'[test]    suite {n%24+1:02d}/24           PASS  ({8+n%17}ms)',
  f'[trace]   request({n:04d})             answer -> generated',
  f'[render]  frame {n*144:06d}           screen -> complete',
  f'[stream]  accepted {n*314:07d} tokens    waiting for next input',
 ]
 return choices[n%8]


CURSOR_TIME_SCALE=.5

def render_terminal_cursor(core,t,start=83,vocal_time=None):
 vocal_time=t if vocal_time is None else vocal_time;u=(t-start)*CURSOR_TIME_SCALE
 im=terminal_base('stdout — live output').copy();d=ImageDraw.Draw(im)
 # Output scrolls continuously; the active head follows the newest typed character.
 speed=3.8;position=u*speed+220;line=int(position);q=position-line
 clip=Image.new('RGBA',(1640,626));cd=ImageDraw.Draw(clip)
 for j in range(15):
  n=line-14+j;y=16+j*47-q*47
  cd.text((2,y),output_line(n),font=mono(30),fill=CYAN if n%5==0 else (PURPLE if n%3==0 else '#789dad'))
 im.paste(clip,(148,137),clip)
 d=ImageDraw.Draw(im);s=output_line(line+1);chars=min(len(s),int(q*len(s)))
 d.rectangle((135,760,1782,855),fill='#0b2430')
 d.text((150,790),s[:chars],font=mono(31),fill='#bafde2')
 cursor_x=150+mono(31).getlength(s[:chars])+49
 d.line((cursor_x-24,842,cursor_x+24,842),fill=CYAN,width=3)
 head(core,im,vocal_time,cursor_x,794,99,3*math.sin(u*2.2))
 d.text((147,878),f'LIVE   stdout  {line+1:05d}   •   streaming',font=mono(23),fill='#7caaa9')
 d.text((1423,878),'UTF-8  •  RUNNING',font=mono(22),fill=CYAN)
 return im


@lru_cache(maxsize=2)
def ascii_figure(core,opened):
 """Sample the shared human mesh into colored, monospaced ASCII glyphs."""
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
 guy.c={**guy.c,'skin':'#87e2c6','jacket':'#8182d7','pants':'#397a8f','hair':'#6576ae','shirt':'#285262'}
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
   k=(x//cw*31+y//ch*17)%13
   char='{}[]01/+=*#@%'[k]
   fill=tuple(np.clip(rgb*1.2+10,0,255).astype(int))
   d.text((x,y-2),char,font=mono(18),fill=fill)
 # Keep the same face readable within the glyph silhouette, at ASCII resolution.
 for x in [930,990]:
  d.rectangle((x-12,231,x+12,253),fill=(0,0,0,0))
  d.text((x,239),'-',font=mono(22),fill='#66adad',anchor='mm')
 d.rectangle((945,277,975,301),fill=(0,0,0,0))
 d.text((960,285),'[]' if opened else '__',font=mono(21),fill='#65b8b4',anchor='mm')
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


def render_ascii(core,t,start=116,vocal_time=None):
 vocal_time=t if vocal_time is None else vocal_time;u=t-start
 im=terminal_base('terminal — assemble performer').copy();d=ImageDraw.Draw(im)
 d.text((147,151),'$ assemble singer --from ascii',font=mono(25),fill=CYAN)
 stages=['[load]  voice.txt','[scan]  hands.txt','[link]  memory.txt','[build] human.stdout']
 for i,s in enumerate(stages):
  if u>.35+i*.8:d.text((147,226+i*44),s,font=mono(23),fill='#6d93a9' if i<3 else PURPLE)
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
  s=['0011{}0101','[]::/+=@##','1100<>0010'][j%3]
  d.text((x,y),s,font=mono(24),fill='#294e64' if u<5.5 else '#254458')
 progress=min(1,max(0,u/5.7));d.rectangle((148,889,688,895),fill='#294357')
 d.rectangle((148,889,148+540*progress,895),fill=CYAN)
 d.text((730,875),f'{round(progress*100):3d}%  '+('PERFORMER LINKED' if progress==1 else 'ASSEMBLING GLYPHS'),font=mono(22),fill=CYAN)
 return im


BOUNCE_POINTS=[(345,673),(655,505),(1000,690),(1435,510),(1570,737),(1200,410),(853,511),(500,752)]
BOUNCE_LABELS=['const','await','return','build()','{ joy }','care++','true',';']


@lru_cache(maxsize=1)
def bounce_events(core):
 # Nearest output frame limits audio-to-animation error to half a 30 fps frame.
 return tuple(sorted(set(round(b*core.FPS)/core.FPS for b in core.DRUM_BEATS)))


def bounce_state(core,t,clip_start=150):
 events=bounce_events(core);i=bisect.bisect_right(events,t+1e-8)-1
 if i<0:return 0,1,float('inf')
 age=max(0,t-events[i])
 if events[i]+1e-8<clip_start:return i,1,float('inf')
 # One short, triggered hop, then a complete hold until another real drum attack.
 return i,min(1,age/.22),age


def render_head_bounce(core,t,start=150,vocal_time=None):
 vocal_time=t if vocal_time is None else vocal_time;u=t-start
 im=terminal_base('src/remember.ts — live execution').copy();d=ImageDraw.Draw(im)
 lines=['async function remember() {','  const joy = await build();','  for (const line of source) {','    if (line.isBroken()) {','      await repair(line);','      care += effort;','    }','  }','  return joy;','}']
 # Dense editor text gives each jump a place within the code, beneath the bright words.
 for column in range(3):
  for j in range(13):
   y=152+j*52;line=lines[(j+column*3)%len(lines)]
   d.text((145+column*552,y),f'{column*13+j+1:02d}',font=mono(20),fill='#284052')
   d.text((192+column*552,y),line,font=mono(22),fill='#304d65' if j%3 else '#3f476a')
 # Use measured audio onsets, including during the later montage reprise.
 i,q,age=bounce_state(core,vocal_time,vocal_time-u)
 active=(i-1)%len(BOUNCE_POINTS);nxt=i%len(BOUNCE_POINTS)
 for j,((x,y),label) in enumerate(zip(BOUNCE_POINTS,BOUNCE_LABELS)):
  color=CYAN if j==active and age<.12 else ('#9989d0' if j%2 else '#5698ad')
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
 d=ImageDraw.Draw(im);d.text((150,878),'EXECUTION   •   step / jump / return',font=mono(23),fill='#77a8b6')
 return im


@lru_cache(maxsize=1)
def montage_cuts(core):
 """Directed opening of the montage, followed by the existing closing cuts."""
 cuts=[(165,167.8183,'bounce'),(167.8183,172,'cursor'),(172,174.4348,'singer_close'),
       (174.4348,176.71,'stage_low'),(176.71,178.89,'typing'),
       (178.89,181.09,'success'),(181.09,183,'stage_wide')]
 return [dict(start=a,end=b,scene=scene) for a,b,scene in cuts]


def render_montage(core,t):
 from digital_scenes import render_coding,render_digital
 cut=next(c for c in montage_cuts(core) if c['start']<=t<c['end'])
 start,end,scene=cut['start'],cut['end'],cut['scene'];u=t-start
 if scene=='singer_close':return core.performance_frame(t,(start,'spot','portrait','hands'),end)
 if scene.startswith('stage_'):
  kind,cam,pose={'stage_wide':('stage','wide','open'),'stage_profile':('stage','profile','hands'),'stage_split':('split','duet','hands'),'stage_low':('stage','low','rise')}[scene]
  return core.performance_frame(t,(start,kind,cam,pose),end)
 if scene=='cursor':return render_terminal_cursor(core,83+u,vocal_time=t)
 if scene=='ascii':return render_ascii(core,116+u/(end-start)*6.9,vocal_time=t)
 if scene=='bounce':return render_head_bounce(core,150+u,vocal_time=t)
 if scene=='parser':return render_digital(core,74.42+u*.85,vocal_time=t)
 if scene=='repair':return render_digital(core,79.71+u/(end-start)*3.25,vocal_time=t)
 if scene=='typing':return render_coding(core,21.5+min(3.3,u))
 if scene=='success':return render_coding(core,25+min(2.2,u*1.7))
 raise ValueError(scene)

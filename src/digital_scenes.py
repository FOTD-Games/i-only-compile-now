"""Animated coding inserts and a continuous journey through a world made of code."""
from functools import lru_cache
import math
import re
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W,H=1920,1080
INK='#d1e7ed';CYAN='#65edda';PINK='#f17d9e';PURPLE='#a798eb'

@lru_cache(maxsize=40)
def mono(size):
 import os
 return ImageFont.truetype(os.environ.get('IDCA_MONO_FONT','/System/Library/Fonts/Menlo.ttc'),size)

def ease(x):
 x=max(0,min(1,x));return x*x*(3-2*x)

def syntax(d,xy,text,size=28,alpha=255):
 x,y=xy
 for word in re.split(r"('[^']*'|\b(?:export|function|const|let|for|of|return|if|await|async|throw|new)\b|\d+|[{}();])",text):
  c=PURPLE if word in ['export','function','const','let','for','of','return','if','await','async','throw','new'] else ('#b9db99' if word.startswith("'") else (CYAN if word in '{}();' else INK))
  if word:d.text((x,y),word,font=mono(size),fill=c);x+=mono(size).getlength(word)

def window(d,rect,title):
 x,y,r,b=rect
 d.rounded_rectangle(rect,radius=14,fill='#101b2c',outline='#3b5871',width=2)
 d.rounded_rectangle((x,y,r,y+53),radius=14,fill='#213148')
 d.rectangle((x+1,y+30,r-1,y+53),fill='#213148')
 for i,c in enumerate(['#d87c9b','#9d98d9','#6ed0bc']):d.ellipse((x+21+i*24,y+20,x+32+i*24,y+31),fill=c)
 d.text((x+115,y+15),title,font=mono(21),fill='#a6bed0')

def coding_editor(t):
 im=Image.new('RGB',(W,H),'#080f1d');d=ImageDraw.Draw(im)
 window(d,(86,65,1834,915),'count-wins.ts  —  editor')
 d.rectangle((87,118,385,878),fill='#132034');d.line((385,118,385,878),fill='#34465b',width=2)
 for i,(s,c) in enumerate([('EXPLORER','#768fa7'),('project/',INK),('  src/',INK),('    count-wins.ts',CYAN),('  package.json',INK),('  tests/',INK)]):d.text((112,154+i*43),s,font=mono(21),fill=c)
 lines=['export function sumWins(wins: number[]) {','  let total = 0;','  for (const win of wins) {','    total += win;','  }','  return total;','}']
 fixed=t>=23.55
 if not fixed:lines[5]='  return totla;'
 for i,s in enumerate(lines):
  y=175+i*66;d.text((423,y),str(i+1).rjust(2),font=mono(28),fill='#536b83');syntax(d,(507,y),s,31)
  if i==5:
   if not fixed:
    points=[(674+k*7,y+40+(3 if k%2 else -3)) for k in range(15)];d.line(points,fill=PINK,width=3)
   else:d.rounded_rectangle((490,y-5,850,y+45),radius=4,outline='#55b89d',width=2)
 if t<24.7:
  xx=507+mono(31).getlength(lines[5]);yy=175+5*66
  if int(t*5)%2==0:d.rectangle((xx,yy,xx+3,yy+38),fill=CYAN)
 d.line((386,708,1833,708),fill='#354a62',width=2)
 d.text((420,733),'TERMINAL',font=mono(21),fill='#91a8bd')
 prompt='$ npm run build';n=max(0,min(len(prompt),int((t-24.1)*32)))
 d.text((425,783),prompt[:n],font=mono(29),fill=CYAN)
 d.rectangle((87,878,1833,914),fill='#184341' if fixed else '#3c253a')
 d.text((110,884),'0 problems   •   saved' if fixed else '1 problem   •   Cannot find name: totla',font=mono(21),fill='#b9ded8' if fixed else '#efb2c7')
 return im

def successful_terminal(t):
 im=Image.new('RGB',(W,H),'#070f1b');d=ImageDraw.Draw(im)
 window(d,(105,75,1815,914),'project — build')
 d.text((159,183),'$ npm run build',font=mono(35),fill=CYAN)
 messages=[(25.0,'> tsc && bundle src/count-wins.ts',INK),(25.18,'[check] TypeScript: no errors',INK),(25.42,'[test]  All 12 tests passed',INK),(25.65,'[build] Generating production files...',INK),(26.0,'BUILD SUCCEEDED',CYAN),(26.0,'1 stubborn bug fixed. This one is mine.','#a6bfc9')]
 for i,(when,s,c) in enumerate(messages):
  if t>=when:d.text((159,300+i*78),s,font=mono(44 if i==4 else 30),fill=c)
 if t>=26.3:
  d.text((159,817),'$',font=mono(32),fill=CYAN)
  if int(t*2)%2==0:d.rectangle((196,822,213,854),fill=CYAN)
 return im

def render_coding(core,t):
 if t<25:return core.desk_frame(t,'typing',coding_editor(t))
 if t<27.4:return successful_terminal(t)
 return core.desk_frame(t,'idle',successful_terminal(t))

CUTS=[(68,'terminal'),(74.42,'parser'),(79.71,'repair'),(83.31,'files'),(91.93,'keys'),(97.41,'care')]

@lru_cache(maxsize=8)
def background(kind):
 yy,xx=np.mgrid[0:H:3,0:W:3];g=np.exp(-(((xx*3/W-.5)/.65)**2+((yy*3/H-.4)/.7)**2)*2)[...,None]
 arr=np.array([5,11,25])+g*np.array([12,27,41]);im=Image.fromarray(np.uint8(arr)).resize((W,H),Image.Resampling.BILINEAR);d=ImageDraw.Draw(im)
 # A virtual floor recedes behind the editor windows, with no physical stage.
 for x in range(-1500,3400,170):d.line((960,550,x,1080),fill='#153a4c',width=1)
 for y in [649,706,770,843,930,1035]:d.line((0,y,W,y),fill='#1b3c50',width=1)
 if kind in ['repair','care']:
  window(d,(110,88,1810,869),'src/joy.ts  —  editor' if kind=='repair' else 'src/care.ts  —  editor')
  lines=['export function findJoy() {','  const effort = solveOneSmallBug();','  const joy = learnByDoing(effort);','  ___________','}'] if kind=='repair' else ['export function keepCreating() {','  const care = rememberWhy();','  const proof = makeSomething(care);','  ___________','}']
  for i,s in enumerate(lines):
   y=187+i*69;d.text((146,y),str(i+1),font=mono(26),fill='#556d82');syntax(d,(212,y),s,34)
  d.line((202,434,548,434),fill='#ab617d',width=2)
  d.text((149,815),'PROBLEMS  1     Missing statement',font=mono(22),fill='#bf7e9a')
 elif kind=='keys':
  window(d,(184,93,1736,702),'memory://keyboard  —  input stream')
  for i,line in enumerate(['const keys = await remember();','for (const key of keys) {','  reach(key);','}','// The cursor keeps moving.']):syntax(d,(250,191+i*77),line,34)
 else:
  title={'terminal':'terminal://watch — live output','parser':'src/parser.ts  —  editor','files':'workspace://generated — live files'}[kind]
  window(d,(125,105,1795,805),title)
  if kind=='terminal':
   for i,s in enumerate(['$ watch ./src --follow','> compiling the night...','> parser.ts:17 unexpected token','> retrying...','> waiting for a human fix']):d.text((193,215+i*71),s,font=mono(32),fill=CYAN if i==0 else ('#c28aa7' if i==2 else '#7395aa'))
  elif kind=='parser':
   for i,s in enumerate(['function parse(input: string) {','  const tokens = scan(input);','  for (const token of tokens) {','    if (token.ready) {','      return next(token);','    }','  }','}']):syntax(d,(220,191+i*65),s,31)
  else:
   for i,s in enumerate(['screen.tsx','logic.ts','routes.ts','styles.css','tests.spec.ts']):d.text((178,201+i*95),s,font=mono(29),fill='#7c9aab')
 return im

def token(im,text,x,y,angle=0,size=33,c=CYAN):
 f=mono(size);width=round(f.getlength(text))+26;patch=Image.new('RGBA',(width,size+26));d=ImageDraw.Draw(patch)
 d.rounded_rectangle((0,0,width-1,size+24),radius=7,fill='#112b3b',outline=c,width=2)
 d.text((13,8),text,font=f,fill=c)
 if angle:patch=patch.rotate(angle,resample=Image.Resampling.BICUBIC,expand=True)
 im.paste(patch,(round(x-patch.width/2),round(y-patch.height/2)),patch)

@lru_cache(maxsize=2)
def digital_human_class(core):
 class DigitalHuman(core.Human):
  def poly(self,p,c,shade=True,head=False):
   super().poly(p,c,shade,head)
   if shade:self.sc.line(self.tr(list(p)+[p[0]],head),'#3d8a9b',.48)
 return DigitalHuman

def avatar(core,im,t,x,foot,pose='run',progress=0,scale=.78,vocal_time=None):
 class View:
  pos=np.array([150.,240.,1000.])
  def project(self,points):
   a=np.asarray(points);return np.stack([x/1.5+1.11*(a[:,0]+a[:,2]*.05),foot/1.5-1.11*a[:,1]+.02*a[:,2]],axis=1),1000-a[:,2]
 cam=View();layer=Image.new('RGBA',(W,H));sc=core.Scene(cam)
 guy=digital_human_class(core)(sc,t,0,0,0,pose,progress,cam,scale)
 guy.c=dict(skin='#70c5d0',jacket='#315f94',pants='#143951',hair='#204e64',shirt='#0c2a3c',accent='#a3ffe7')
 if pose=='repair':guy.R=core.rot(.05,1.07,-.1*(1-ease(progress)))
 guy.draw(True,vocal_time);sc.paint(layer)
 bounds=layer.getbbox()
 if bounds:
  crop=layer.crop(bounds);glow=Image.new('RGBA',crop.size,'#20dcb8');glow.putalpha(crop.getchannel('A').filter(ImageFilter.GaussianBlur(9)).point(lambda a:round(a*.24)))
  im.paste(glow,bounds[:2],glow);im.paste(crop,bounds[:2],crop)

def platform(d,y,t,c=CYAN):
 d.line((0,y,W,y),fill='#244e62',width=8);d.line((0,y-3,W,y-3),fill=c,width=2)
 for x in range(-180,W+180,180):
  xx=x-int(t*135)%180;d.text((xx,y+23),'{  }',font=mono(29),fill='#315568')

def repair_scene(core,im,t,start,kind,vocal_time=None):
 u=t-start;care=kind=='care'
 # The statement falls, is caught, lifted, and snapped back into the actual code line.
 floor_y=828;x=830+100*ease(u/.7)
 lift=ease((u-1.1)/1.2);fixed=u>=2.3
 exiting=care and u>2.7
 avatar(core,im,t,x+(900*ease((u-2.7)/.89) if exiting else 0),floor_y,'run' if u<.65 or exiting else 'repair',lift,.80,vocal_time)
 label='return joy;' if not care else 'return care;'
 source=np.array([414.,417.]);ground=np.array([1090.,780.])
 if u<.62:
  q=max(0,u/.62);pos=source+(ground-source)*q*q;angle=-18*q
 elif u<1.1:pos=ground;angle=-18
 elif not fixed:
  pos=ground*(1-lift)+source*lift;pos[1]-=100*math.sin(lift*math.pi);angle=-18*(1-lift)
 else:pos=source;angle=0
 d=ImageDraw.Draw(im)
 if not fixed:token(im,label,float(pos[0]),float(pos[1]),angle,31,'#f096bb' if u<1.1 else CYAN)
 else:
  d.rectangle((202,388,701,443),fill='#103b3b');syntax(d,(212,394),label,34)
  d.rectangle((130,799,895,850),fill='#102333');d.text((149,815),'PROBLEMS  0     Statement restored',font=mono(22),fill=CYAN)
  for i in range(16):
   age=min(.8,u-2.3);a=i*math.tau/16;xx=414+math.cos(a)*age*260;yy=417+math.sin(a)*age*170
   d.rectangle((xx,yy,xx+5,yy+5),fill='#8dffe0')
 if care:
  # The last repair resolves into a running exit through the terminal edge.
  d.line((1735,230,1735,826),fill='#53e3d0',width=5)
  d.line((1760,265,1760,826),fill='#41699b',width=3)

def render_digital(core,t,vocal_time=None):
 start,kind=max((cut for cut in CUTS if cut[0]<=t),key=lambda c:c[0]);u=t-start
 im=background(kind).copy();d=ImageDraw.Draw(im)
 if kind in ['repair','care']:
  repair_scene(core,im,t,start,kind,vocal_time)
 elif kind=='terminal':
  platform(d,825,t);x=965+95*math.sin(u*.56)
  for j in range(6):
   xx=(1550+j*377-u*182)%2450-220
   d.text((xx,623+(j%2)*65),['> compiling','> watch','> retry'][j%3],font=mono(27),fill='#386b80')
  avatar(core,im,t,x,825,'run',vocal_time=vocal_time)
  # A bracket gate passes over the runner as he moves through the terminal.
  gate=1770-u*150;d.text((gate,375),'}',font=mono(290),fill='#3a7c8b')
 elif kind=='parser':
  # Editor lines become staggered ledges. The runner clears the gaps.
  x=880+150*math.sin(u*.52);cycle=(u%2.1)/2.1;jump=138*max(0,math.sin(cycle*math.pi))
  for j in range(7):
   xx=j*385-(u*150)%385-200;yy=812-(j%2)*60
   d.rounded_rectangle((xx,yy,xx+310,yy+37),radius=5,fill='#15334a',outline='#5caebb',width=2)
   d.text((xx+12,yy+5),['if (ready) {','return next;','}'][j%3],font=mono(22),fill=CYAN)
  avatar(core,im,t,x,820-jump,'jump',vocal_time=vocal_time)
 elif kind=='files':
  platform(d,825,t);x=930+80*math.sin(u*.65)
  # New editor windows stream past faster than the human can inspect them.
  for j in range(4):
   xx=(1820+j*660-u*235)%2640-470;yy=195+(j%2)*124
   patch=Image.new('RGBA',(470,300));pd=ImageDraw.Draw(patch);window(pd,(0,0,469,299),['screen.tsx','logic.ts','routes.ts','joy.ts'][j])
   for k,s in enumerate(['const view = build();','export function run() {','  return view;','}']):syntax(pd,(24,77+k*44),s,20)
   im.paste(patch,(round(xx),yy),patch)
  avatar(core,im,t,x,825,'run',vocal_time=vocal_time)
  # Loose punctuation drops out of the generated files; the avatar repairs it in stride.
  q=(u%3.1)/3.1;frag_x=x+125;frag_y=380+390*min(1,q/.35)**2 if q<.5 else 770-390*ease((q-.5)/.4)
  token(im,'}',frag_x,frag_y,20*math.sin(q*math.pi),52,PINK if q<.5 else CYAN)
 elif kind=='keys':
  x=935+70*math.sin(u*.9);cycle=(u%2.2)/2.2;jump=70*max(0,math.sin(cycle*math.pi))
  # Giant keys peel away underneath his feet while he reaches into empty space.
  for j in range(12):
   xx=j*198-(u*135)%198-140;fall=max(0,(x-xx-260)/600);yy=803+240*fall*fall
   if yy>1040:continue
   token(im,['{','}','⌘','K',';','R','E','T','U','R','N','↵'][j],xx,yy,fall*20,44,'#55adaf')
  avatar(core,im,t,x,790-jump,'jump',scale=.83,vocal_time=vocal_time)
 # Scan lines and subtle moving packets belong to the environment, not the lyric layer.
 scan=Image.new('RGBA',(W,H));sd=ImageDraw.Draw(scan)
 for y in range(int(t*25)%6,925,6):sd.line((0,y,W,y),fill=(5,16,29,60),width=1)
 im=Image.alpha_composite(im.convert('RGBA'),scan).convert('RGB');d=ImageDraw.Draw(im)
 for i in range(16):
  xx=(i*137+t*(25+i%3*15))%W;yy=105+(i*73)%680
  d.rectangle((xx,yy,xx+3,yy+3),fill='#50878c')
 if t<68.35:
  # A brief data-slice entrance establishes that this is the same character digitized.
  amount=1-ease((t-68)/.35)
  for j in range(8):
   yy=155+j*89;shift=round(amount*70*math.sin(j*3))
   strip=im.crop((0,yy,W,yy+12));im.paste(strip,(shift,yy))
 return im

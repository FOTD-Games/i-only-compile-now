"""1960 coding inserts (coding form, keypunch, listing) and a journey through the 704."""
from functools import lru_cache
import math
import re
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from timeline import T

W,H=1920,1080
# Names kept from upstream; values are console amber, lamp red and IBM blue-white on cream ink.
INK='#ece4cc';CYAN='#ffbf5a';PINK='#ff7062';PURPLE='#9ec4ff'
PAPER='#efe9d6';PENCIL='#3b3a38';RED_PENCIL='#b23a30'

@lru_cache(maxsize=40)
def mono(size):
 import os
 from render_video import MONO_FONT
 return ImageFont.truetype(MONO_FONT,size)

def ease(x):
 x=max(0,min(1,x));return x*x*(3-2*x)

FORTRAN_WORDS={'DO','GO TO','IF','CALL','CONTINUE','FORMAT','PRINT','READ','END','STOP','FUNCTION','SUBROUTINE','RETURN','DIMENSION'}

def syntax(d,xy,text,size=28,alpha=255):
 x,y=xy
 for word in re.split(r"(\b(?:DO|GO TO|IF|CALL|CONTINUE|FORMAT|PRINT|READ|END|STOP|FUNCTION|SUBROUTINE|RETURN|DIMENSION)\b|\d+|[(),=])",text):
  c=PURPLE if word in FORTRAN_WORDS else (CYAN if word in '(),=' else ('#e3b98a' if word.strip().isdigit() else INK))
  if word:d.text((x,y),word,font=mono(size),fill=c);x+=mono(size).getlength(word)

def window(d,rect,title):
 # A console panel: steel bezel, engraved label plate, two indicator lamps.
 x,y,r,b=rect
 d.rectangle(rect,fill='#15130f',outline='#6b7178',width=3)
 d.rectangle((x,y,r,y+53),fill='#3c4249')
 for i,c in enumerate(['#ffbf5a','#ff7062']):d.ellipse((x+21+i*26,y+18,x+35+i*26,y+32),fill=c)
 d.rectangle((x+90,y+12,x+110+mono(21).getlength(title),y+42),fill='#d9d2bd')
 d.text((x+100,y+15),title,font=mono(21),fill='#26231f')

FORM=['C     COUNT MY WINS','      TOTAL = 0.0','      DO 10 I = 1, N','   10 TOTAL = TOTAL + WINS(I)','      PRINT 20, TOTAL','   20 FORMAT (6H WINS=, F8.0)','      STOP','      END']

def coding_form(d,t,fixed):
 d.rectangle((86,65,1834,915),fill=PAPER,outline='#9c937c',width=2)
 d.text((120,88),'FORTRAN CODING FORM',font=mono(30),fill='#5b6e57')
 d.text((640,96),'PROGRAM  COUNT WINS        PROGRAMMER  J. D.        DATE  3/14/60',font=mono(21),fill='#6b6a5f')
 cw=mono(31).getlength('M');x0=150
 # Column bands: statement number 1-5, continuation 6, statement 7-72, identification 73-80.
 for col,label in [(0,'STMT'),(5,'C'),(6,'FORTRAN STATEMENT'),(42,'IDENT')]:d.text((x0+col*cw+4,140),label,font=mono(17),fill='#7b8a72')
 for col in [5,6,42]:d.line((x0+col*cw,135,x0+col*cw,650),fill='#a9b79c',width=2)
 for k in range(9):d.line((100,165+k*62,1820,165+k*62),fill='#c3cdb5',width=1)
 lines=list(FORM)
 if not fixed:lines[4]='      PRINT 20, TOTLA'
 for i,line in enumerate(lines):
  y=176+i*62;d.text((x0,y),line,font=mono(31),fill=PENCIL)
  d.text((x0+42*cw+8,y+4),f'CW{i+1:02d}0',font=mono(22),fill='#8a8574')
  if i==4:
   xx=x0+16*cw
   if not fixed:d.ellipse((xx-12,y-8,xx+5*cw+12,y+44),outline=RED_PENCIL,width=3)
   else:d.line((xx+5*cw+20,y+22,xx+5*cw+32,y+34,xx+5*cw+56,y+4),fill='#3f7a46',width=4)
 return x0,cw

def coding_editor(t):
 im=Image.new('RGB',(W,H),'#17120f');d=ImageDraw.Draw(im)
 t0=T['coding']['start'];fixed=t>=t0+2.05
 x0,cw=coding_form(d,t,fixed)
 if t<t0+3.2 and int(t*5)%2==0:
  # The pencil point rests where the correction goes.
  xx=x0+21*cw;yy=176+4*62;d.polygon([(xx,yy+30),(xx+14,yy-6),(xx+28,yy-2)],fill='#d9a441')
 d.line((100,700,1820,700),fill='#9c937c',width=2)
 d.text((120,724),'JOB TICKET',font=mono(21),fill='#6b6a5f')
 prompt='SUBMIT DECK TO OPERATOR  -  RUN 0412';n=max(0,min(len(prompt),int((t-t0-2.6)*32)))
 d.text((125,774),prompt[:n],font=mono(31),fill=PENCIL)
 d.rectangle((87,878,1833,914),fill='#d6e6cf' if fixed else '#f0d4c8')
 d.text((110,884),'NO DIAGNOSTICS   -   DECK PUNCHED' if fixed else '1 DIAGNOSTIC   -   UNDEFINED VARIABLE  TOTLA',font=mono(21),fill='#2f5a36' if fixed else RED_PENCIL)
 return im

def successful_terminal(t):
 from render_video import greenbar,print_font,INK as PRINT_INK
 im=greenbar(29).copy();d=ImageDraw.Draw(im)
 d.text((262,90),'RUN 0412     FORTRAN II     IBM 704          COUNT WINS',font=print_font(30),fill='#6f6a5f')
 s0=T['coding']['success']
 messages=[(s0,'SOURCE STATEMENTS ..........   8'),(s0+.18,'DIAGNOSTICS ................ NONE'),(s0+.42,'OBJECT DECK PUNCHED ........  97 CARDS'),(s0+.65,'EXECUTION BEGINS'),(s0+1,'EXECUTION COMPLETE'),(s0+1,'WINS =      12.     THIS ONE IS MINE.')]
 for i,(when,line) in enumerate(messages):
  if t>=when:d.text((262,210+i*84),line,font=print_font(50 if i==4 else 34),fill=PRINT_INK)
 if t>=s0+1.3:
  d.text((262,780),'END OF JOB',font=print_font(34),fill=PRINT_INK)
  if int(t*2)%2==0:d.rectangle((262,836,282,870),fill=PRINT_INK)
 return im

def render_coding(core,t):
 if t<T['coding']['success']:return core.desk_frame(t,'typing',coding_editor(t))
 if t<T['coding']['idle']:return successful_terminal(t)
 return core.desk_frame(t,'idle',successful_terminal(t))

CUTS=[tuple(c) for c in T['digital']['cuts']]

@lru_cache(maxsize=8)
def background(kind):
 yy,xx=np.mgrid[0:H:3,0:W:3];g=np.exp(-(((xx*3/W-.5)/.65)**2+((yy*3/H-.4)/.7)**2)*2)[...,None]
 arr=np.array([10,9,8])+g*np.array([38,30,20]);im=Image.fromarray(np.uint8(arr)).resize((W,H),Image.Resampling.BILINEAR);d=ImageDraw.Draw(im)
 # A virtual floor recedes behind the editor windows, with no physical stage.
 for x in range(-1500,3400,170):d.line((960,550,x,1080),fill='#3a2c1c',width=1)
 for y in [649,706,770,843,930,1035]:d.line((0,y,W,y),fill='#40301d',width=1)
 if kind in ['repair','care']:
  window(d,(110,88,1810,869),'FINDJOY  -  SOURCE DECK' if kind=='repair' else 'KEEPON  -  SOURCE DECK')
  lines=['C     FIND JOY','EFFORT = SOLVE(BUG)','JOY = LEARN(EFFORT)','___________','END'] if kind=='repair' else ['C     KEEP CREATING','CARE = REMEMBER(WHY)','PROOF = MAKE(CARE)','___________','END']
  for i,s in enumerate(lines):
   y=187+i*69;d.text((146,y),str(i+1),font=mono(26),fill='#556d82');syntax(d,(212,y),s,34)
  d.line((202,434,548,434),fill=PINK,width=2)
  d.text((149,815),'DIAGNOSTIC 1     MISSING STATEMENT',font=mono(22),fill=PINK)
 elif kind=='keys':
  window(d,(184,93,1736,702),'KEYPUNCH  -  INPUT DECK')
  for i,line in enumerate(['READ 5, KEYS','DO 40 K = 1, N','   CALL REACH(KEYS(K))','40 CONTINUE','C  THE CARRIAGE KEEPS MOVING.']):syntax(d,(250,191+i*77),line,34)
 else:
  title={'terminal':'CONSOLE TYPEWRITER  -  LIVE OUTPUT','parser':'PARSE  -  SOURCE DECK','files':'TAPE 3  -  GENERATED DECKS'}[kind]
  window(d,(125,105,1795,805),title)
  if kind=='terminal':
   for i,s in enumerate(['* WATCH SOURCE DECK','COMPILING THE NIGHT ...','CARD 17   ILLEGAL CHARACTER','RETRYING ...','WAITING FOR A HUMAN FIX']):d.text((193,215+i*71),s,font=mono(32),fill=CYAN if i==0 else (PINK if i==2 else '#b59a74'))
  elif kind=='parser':
   for i,s in enumerate(['FUNCTION PARSE(INPUT)','CALL SCAN(INPUT, TOKENS)','DO 30 J = 1, N','IF (READY(J)) 20, 30, 30','20 PARSE = NEXT(J)','RETURN','30 CONTINUE','END']):syntax(d,(220,191+i*65),s,31)
  else:
   for i,s in enumerate(['PAYROLL DECK','ORBIT DECK','INVENTORY DECK','TABLES DECK','TEST DECK']):d.text((178,201+i*95),s,font=mono(29),fill='#b59a74')
 return im

def token(im,text,x,y,angle=0,size=33,c=CYAN):
 f=mono(size);width=round(f.getlength(text))+26;patch=Image.new('RGBA',(width,size+26));d=ImageDraw.Draw(patch)
 d.rounded_rectangle((0,0,width-1,size+24),radius=4,fill='#1f1a14',outline=c,width=2)
 d.text((13,8),text,font=f,fill=c)
 if angle:patch=patch.rotate(angle,resample=Image.Resampling.BICUBIC,expand=True)
 im.paste(patch,(round(x-patch.width/2),round(y-patch.height/2)),patch)

@lru_cache(maxsize=2)
def digital_human_class(core):
 class DigitalHuman(core.Human):
  def poly(self,p,c,shade=True,head=False):
   super().poly(p,c,shade,head)
   if shade:self.sc.line(self.tr(list(p)+[p[0]],head),'#c98a3a',.48)
 return DigitalHuman

def avatar(core,im,t,x,foot,pose='run',progress=0,scale=.78,vocal_time=None):
 class View:
  pos=np.array([150.,240.,1000.])
  def project(self,points):
   a=np.asarray(points);return np.stack([x/1.5+1.11*(a[:,0]+a[:,2]*.05),foot/1.5-1.11*a[:,1]+.02*a[:,2]],axis=1),1000-a[:,2]
 cam=View();layer=Image.new('RGBA',(W,H));sc=core.Scene(cam)
 guy=digital_human_class(core)(sc,t,0,0,0,pose,progress,cam,scale)
 guy.c={**core.CAST[0],'skin':'#f0c27a','jacket':'#e9d8b0','pants':'#5b3418','hair':'#4a2a12','shirt':'#e9d8b0','accent':'#9a5b2a'}
 if pose=='repair':guy.R=core.rot(.05,1.07,-.1*(1-ease(progress)))
 guy.draw(True,vocal_time);sc.paint(layer)
 bounds=layer.getbbox()
 if bounds:
  crop=layer.crop(bounds);glow=Image.new('RGBA',crop.size,'#ffb347');glow.putalpha(crop.getchannel('A').filter(ImageFilter.GaussianBlur(9)).point(lambda a:round(a*.24)))
  im.paste(glow,bounds[:2],glow);im.paste(crop,bounds[:2],crop)

def platform(d,y,t,c=CYAN):
 # The floor is a deck of cards running past, numbered in columns 73-80.
 d.line((0,y,W,y),fill='#5b4526',width=8);d.line((0,y-3,W,y-3),fill=c,width=2)
 shift=int(t*135)
 for x in range(-180,W+180,180):
  xx=x-shift%180;n=(x+180)//180+shift//180
  d.text((xx,y+23),f'{n*10:08d}',font=mono(24),fill='#7a6340')

def repair_scene(core,im,t,start,kind,vocal_time=None):
 u=t-start;care=kind=='care'
 # The statement falls, is caught, lifted, and snapped back into the actual code line.
 floor_y=828;x=830+100*ease(u/.7)
 lift=ease((u-1.1)/1.2);fixed=u>=2.3
 exiting=care and u>2.7
 avatar(core,im,t,x+(900*ease((u-2.7)/.89) if exiting else 0),floor_y,'run' if u<.65 or exiting else 'repair',lift,.80,vocal_time)
 label='FINDJOY = JOY' if not care else 'KEEPON = CARE'
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
  d.rectangle((202,388,701,443),fill='#3a2a12');syntax(d,(212,394),label,34)
  d.rectangle((130,799,895,850),fill='#15130f');d.text((149,815),'DIAGNOSTICS 0     STATEMENT RESTORED',font=mono(22),fill=CYAN)
  for i in range(16):
   age=min(.8,u-2.3);a=i*math.tau/16;xx=414+math.cos(a)*age*260;yy=417+math.sin(a)*age*170
   d.rectangle((xx,yy,xx+5,yy+5),fill='#ffe0a0')
 if care:
  # The last repair resolves into a running exit through the terminal edge.
  d.line((1735,230,1735,826),fill=CYAN,width=5)
  d.line((1760,265,1760,826),fill=PURPLE,width=3)

def render_digital(core,t,vocal_time=None):
 start,kind=max((cut for cut in CUTS if cut[0]<=t),key=lambda c:c[0]);u=t-start
 im=background(kind).copy();d=ImageDraw.Draw(im)
 if kind in ['repair','care']:
  repair_scene(core,im,t,start,kind,vocal_time)
 elif kind=='terminal':
  platform(d,825,t);x=965+95*math.sin(u*.56)
  for j in range(6):
   xx=(1550+j*377-u*182)%2450-220
   d.text((xx,623+(j%2)*65),['COMPILING','REWIND 3','RETRY'][j%3],font=mono(27),fill='#7a6340')
  # A giant tape reel rolls past behind the runner.
  gx=1770-u*150;gy=560;r=230
  d.ellipse((gx-r,gy-r,gx+r,gy+r),outline='#8a7350',width=10)
  d.ellipse((gx-40,gy-40,gx+40,gy+40),outline='#8a7350',width=8)
  for k in range(3):
   a=-u*1.2+k*math.tau/3;d.line((gx+50*math.cos(a),gy+50*math.sin(a),gx+200*math.cos(a),gy+200*math.sin(a)),fill='#8a7350',width=8)
  avatar(core,im,t,x,825,'run',vocal_time=vocal_time)
 elif kind=='parser':
  # Editor lines become staggered ledges. The runner clears the gaps.
  x=880+150*math.sin(u*.52);cycle=(u%2.1)/2.1;jump=138*max(0,math.sin(cycle*math.pi))
  for j in range(7):
   xx=j*385-(u*150)%385-200;yy=812-(j%2)*60
   # Punched cards as ledges, corner clipped like the real thing.
   d.polygon([(xx+18,yy),(xx+310,yy),(xx+310,yy+37),(xx,yy+37),(xx,yy+18)],fill='#e9e1c6',outline='#8c7d5c')
   d.text((xx+24,yy+5),['DO 30 J=1,N','GO TO 20','CONTINUE'][j%3],font=mono(22),fill='#26231f')
  avatar(core,im,t,x,820-jump,'jump',vocal_time=vocal_time)
 elif kind=='files':
  platform(d,825,t);x=930+80*math.sin(u*.65)
  # New editor windows stream past faster than the human can inspect them.
  for j in range(4):
   xx=(1820+j*660-u*235)%2640-470;yy=195+(j%2)*124
   patch=Image.new('RGBA',(470,300));pd=ImageDraw.Draw(patch);window(pd,(0,0,469,299),['PAYROLL','ORBIT','INVENTORY','JOY'][j])
   for k,s in enumerate(['DIMENSION V(100)','CALL BUILD(V)','RETURN','END']):syntax(pd,(24,77+k*44),s,20)
   im.paste(patch,(round(xx),yy),patch)
  avatar(core,im,t,x,825,'run',vocal_time=vocal_time)
  # Loose punctuation drops out of the generated files; the avatar repairs it in stride.
  q=(u%3.1)/3.1;frag_x=x+125;frag_y=380+390*min(1,q/.35)**2 if q<.5 else 770-390*ease((q-.5)/.4)
  token(im,')',frag_x,frag_y,20*math.sin(q*math.pi),52,PINK if q<.5 else CYAN)
 elif kind=='keys':
  x=935+70*math.sin(u*.9);cycle=(u%2.2)/2.2;jump=70*max(0,math.sin(cycle*math.pi))
  # Giant keys peel away underneath his feet while he reaches into empty space.
  for j in range(12):
   xx=j*198-(u*135)%198-140;fall=max(0,(x-xx-260)/600);yy=803+240*fall*fall
   if yy>1040:continue
   token(im,['&','-','0','1','REL','R','E','T','U','R','N','SKIP'][j],xx,yy,fall*20,44,'#d0a060')
  avatar(core,im,t,x,790-jump,'jump',scale=.83,vocal_time=vocal_time)
 # Scan lines and subtle moving packets belong to the environment, not the lyric layer.
 scan=Image.new('RGBA',(W,H));sd=ImageDraw.Draw(scan)
 for y in range(int(t*25)%6,925,6):sd.line((0,y,W,y),fill=(12,9,4,60),width=1)
 im=Image.alpha_composite(im.convert('RGBA'),scan).convert('RGB');d=ImageDraw.Draw(im)
 for i in range(16):
  xx=(i*137+t*(25+i%3*15))%W;yy=105+(i*73)%680
  d.rectangle((xx,yy,xx+3,yy+3),fill='#a0763a')
 if t<CUTS[0][0]+.35:
  # A brief data-slice entrance establishes that this is the same character digitized.
  amount=1-ease((t-CUTS[0][0])/.35)
  for j in range(8):
   yy=155+j*89;shift=round(amount*70*math.sin(j*3))
   strip=im.crop((0,yy,W,yy+12));im.paste(strip,(shift,yy))
 return im

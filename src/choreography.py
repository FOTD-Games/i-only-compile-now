"""Beat-counted full-body dance phrases for the two chorus performers."""
import math
import numpy as np

MOVES = ('step_touch', 'running_man', 'kick_point', 'grapevine', 'robot',
         'body_roll', 'skater', 'twist', 'overhead_clap', 'pivot_turn')
ROUTINES = (
 ('step_touch', 'running_man', 'kick_point', 'grapevine', 'robot', 'body_roll', 'overhead_clap', 'pivot_turn'),
 ('skater', 'twist', 'robot', 'running_man', 'overhead_clap', 'pivot_turn', 'kick_point', 'grapevine'),
 ('pivot_turn', 'step_touch', 'robot', 'grapevine', 'skater', 'running_man', 'overhead_clap', 'kick_point', 'body_roll', 'twist'),
)
PHRASE_BEATS = 4
BLEND_BEATS = .65


def smooth(x):
 x=max(0,min(1,x));return x*x*(3-2*x)


def pose_for_move(name, beat):
 """Root, body/head rotations and joint targets, in the performer's local space."""
 s=math.sin(math.pi*beat);c=math.cos(math.pi*beat)
 slow=math.sin(math.pi*beat/2);pulse=math.sin(math.pi*beat)**2
 root=np.array([24*s,5*pulse,0.])
 body=np.array([.02*c,.13*slow,.045*s]);head=np.array([.025*s,0.,-.025*s])
 knees=np.array([[-26.,80,10],[26,80,10]])
 feet=np.array([[-36.,12,0],[36,12,0]])
 arms=np.array([[-88.,208+36*s,40],[88,208-36*s,40],[-69,190,12],[69,190,12]])
 if name=='step_touch':
  root[0]=38*s
  for i,side in enumerate([-1,1]):
   lift=max(0,-side*s);feet[i]=[side*(36+21*lift),12+26*lift,8]
   knees[i]=[side*(27+10*lift),80+12*lift,15]
 elif name=='running_man':
  root=np.array([10*slow,7*pulse,18*slow]);body[0]=.10
  for i,side in enumerate([-1,1]):
   step=-side*s;up=max(0,step)
   knees[i]=[side*27,79+59*up,15+44*up]
   feet[i]=[side*32,12+75*up,-50*step]
  arms=np.array([[-46,193+51*s,64-26*s],[46,193-51*s,64+26*s],[-63,181+18*s,5],[63,181-18*s,5]])
 elif name=='kick_point':
  root=np.array([-20*s,4*pulse,-10.]);body=np.array([-.08*pulse,.13*slow,-.07*s])
  for i,side in enumerate([-1,1]):
   kick=max(0,-side*s)**2
   knees[i]=[side*(27+9*kick),80+25*kick,10+65*kick]
   feet[i]=[side*(35+13*kick),12+57*kick,128*kick]
  arms=np.array([[-117,241+64*s,34],[117,241-64*s,34],[-84,214+26*s,16],[84,214-26*s,16]])
 elif name=='grapevine':
  root=np.array([49*slow,3*pulse,8*c]);body=np.array([0.,.24*slow,.07*slow])
  for i,side in enumerate([-1,1]):
   cross=max(0,-side*s);knees[i]=[side*(27-25*cross),83,18+14*cross]
   feet[i]=[side*(44-67*cross),12+18*pulse,side*26*cross]
  arms=np.array([[-128,215+28*slow,22],[128,215-28*slow,22],[-83,202,8],[83,202,8]])
 elif name=='robot':
  # Sharp, deliberate quarter-beat poses, with eased transitions between them.
  q=beat*2;k=math.floor(q);u=smooth((q-k)/.40)
  a=math.sin(k*math.pi/2)*(1-u)+math.sin((k+1)*math.pi/2)*u
  root=np.array([12*a,-10*pulse,0.]);body=np.array([.08*a,.35*a,0.]);head=np.array([-.08*a,-.15*a,0.])
  feet[:,0]*=1.45;knees[:,0]*=1.4;knees[:,1]-=6
  arms=np.array([[-108,223+60*a,18],[108,223-60*a,18],[-106,221,14],[106,221,14]])
 elif name=='body_roll':
  root=np.array([16*slow,-23*(.5+.5*c),12*s]);body=np.array([.17*s,.16*slow,.045*slow])
  head=np.array([-.12*s,0.,.03*slow]);feet[:,0]*=1.45;knees[:,0]*=1.7;knees[:,1]-=7
  arms=np.array([[-47,200+48*c,80+19*s],[47,200+48*c,80+19*s],[-73,183+17*c,35],[73,183+17*c,35]])
 elif name=='skater':
  root=np.array([42*s,-10*pulse,12*slow]);body=np.array([.12*pulse,.17*s,.13*s])
  for i,side in enumerate([-1,1]):
   trail=max(0,-side*s);knees[i]=[side*(31+25*trail),79-12*trail,8]
   feet[i]=[side*(37+64*trail),12+14*trail,-41*trail]
  arms=np.array([[-114,213+54*s,44+25*s],[114,213-54*s,44-25*s],[-83,197+18*s,16],[83,197-18*s,16]])
 elif name=='twist':
  root=np.array([18*s,-8*pulse,0.]);body=np.array([.03,.58*s,.025*s]);head[1]=-.3*s
  knees[:,0]+=[15*s,15*s];feet[:,0]+=[-11*s,-11*s]
  arms=np.array([[-71,241+22*c,58],[71,241-22*c,58],[-80,190,12],[80,190,12]])
 elif name=='overhead_clap':
  clap=max(0,c)**2;open_legs=1-clap;root=np.array([0.,13*pulse,0.]);body*=.25
  feet[:,0]=[-34-25*open_legs,34+25*open_legs];feet[:,1]+=9*pulse
  knees[:,0]=[-28-12*open_legs,28+12*open_legs]
  arms=np.array([[-(68-60*clap),300+40*clap,28],[(68-60*clap),300+40*clap,28],[-76+30*clap,265+14*clap,8],[76-30*clap,265+14*clap,8]])
 elif name=='pivot_turn':
  root=np.array([14*slow,6*pulse,14*c]);body=np.array([.025,1.1*slow,.045*s]);head[1]=-.28*slow
  feet[:,2]=[-26*c,26*c];feet[:,1]+=[18*max(0,s),18*max(0,-s)]
  knees[:,2]=[-15*c,15*c]
  arms=np.array([[-124,224+34*c,22],[124,224-34*c,22],[-83,204+10*c,4],[83,204-10*c,4]])
 else:raise ValueError(name)
 return dict(root=root,body=body,head=head,knees=knees,feet=feet,arms=arms)


def dance_pose(beat, section):
 """One shared pose and transition phase for both chorus dancers."""
 beat=max(0,beat);routine=ROUTINES[section];phrase=int(beat//PHRASE_BEATS)
 name=routine[phrase%len(routine)];previous=routine[max(0,phrase-1)%len(routine)]
 current=pose_for_move(name,beat);old=pose_for_move(previous,beat)
 blend=smooth((beat%PHRASE_BEATS)/BLEND_BEATS) if phrase else 1
 result={key:old[key]*(1-blend)+current[key]*blend for key in current}
 result['name']=name
 return result

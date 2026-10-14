"""Beat-counted swing-era phrases for the two chorus performers (1960 big-band edit)."""
import math
import numpy as np

MOVES = ('lindy_rock', 'charleston', 'suzie_q', 'shorty_george', 'kick_ball_change',
         'jazz_hands', 'shoulder_shimmy', 'snap_sway', 'twist', 'tracking_turn')
ROUTINES = (
 ('lindy_rock', 'snap_sway', 'charleston', 'suzie_q', 'jazz_hands', 'kick_ball_change', 'shoulder_shimmy', 'tracking_turn'),
 ('twist', 'lindy_rock', 'shorty_george', 'charleston', 'snap_sway', 'tracking_turn', 'kick_ball_change', 'jazz_hands'),
 ('tracking_turn', 'lindy_rock', 'charleston', 'suzie_q', 'shorty_george', 'twist', 'snap_sway', 'kick_ball_change', 'shoulder_shimmy', 'jazz_hands'),
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
 if name=='lindy_rock':
  # Rock step back, then the triple step; one hand out to the side, one at the chest.
  root=np.array([22*s,5*pulse,0.]);body=np.array([.06*pulse,.12*slow,.04*s])
  for i,side in enumerate([-1,1]):
   rock=max(0,-side*s);knees[i]=[side*27,80+8*rock,10-10*rock]
   feet[i]=[side*36,12+10*rock,-38*rock]
  arms=np.array([[-112,178+20*s,42],[58,203+6*s,72],[-78,192,18],[72,182,32]])
 elif name=='charleston':
  # Forward kick on one side, back kick on the other; hands swing together over the knees.
  fwd=max(0,s);back=max(0,-s);root=np.array([10*s,6*pulse,6*s]);body=np.array([.08*s,.1*slow,0.])
  knees[0]=[-27+10*c,80+20*fwd,10+45*fwd];feet[0]=[-36+10*c,12+45*fwd,80*fwd]
  knees[1]=[27-10*c,80+15*back,10-20*back];feet[1]=[36-10*c,12+45*back,-70*back]
  arms=np.array([[-70+30*s,160,60],[70+30*s,160,60],[-70+10*s,190,25],[70+10*s,190,25]])
 elif name=='suzie_q':
  # Heel-toe travel to the side with hands clasped at the chest.
  root=np.array([45*slow,-6+4*pulse,0.]);body=np.array([.05,.2*s,.03*s])
  feet[:,2]=[12*s,-12*s];feet[:,0]*=1.15;knees[:,1]-=6
  arms=np.array([[-12,215+6*pulse,62],[12,215+6*pulse,62],[-62,190,30],[62,190,30]])
 elif name=='shorty_george':
  # Low, knees-together walk with arms swinging straight down toward the floor.
  root=np.array([14*s,-22*(.6+.4*pulse),10*s]);body=np.array([.1,.1*s,0.])
  for i,side in enumerate([-1,1]):
   knees[i]=[side*14+12*s,70,40];feet[i]=[side*32,12,15*side*s]
  arms=np.array([[-60+25*s,122,55],[60+25*s,122,55],[-62+12*s,175,22],[62+12*s,175,22]])
 elif name=='kick_ball_change':
  root=np.array([-14*s,4*pulse,-8.]);body=np.array([-.06*pulse,.1*slow,-.05*s])
  for i,side in enumerate([-1,1]):
   kick=max(0,-side*s)**2
   knees[i]=[side*(27+6*kick),80+25*kick,10+60*kick]
   feet[i]=[side*(35+8*kick),12+50*kick,115*kick]
  arms=np.array([[-62,175+25*s,40+40*s],[62,175-25*s,40-40*s],[-66,195,15+15*s],[66,195,15-15*s]])
 elif name=='jazz_hands':
  # Open palms at shoulder height, shaking on the eighth notes, over a step-touch.
  shake=math.sin(4*math.pi*beat);root=np.array([30*s,4*pulse,0.])
  for i,side in enumerate([-1,1]):
   lift=max(0,-side*s);feet[i]=[side*(36+18*lift),12+22*lift,8];knees[i]=[side*(27+8*lift),80+10*lift,15]
  arms=np.array([[-122,252+7*shake,55],[122,252-7*shake,55],[-92,205,25],[92,205,25]])
 elif name=='shoulder_shimmy':
  q=math.sin(4*math.pi*beat);root=np.array([8*s,-8.,0.]);body=np.array([-.05,.13*q,.03*q])
  feet[:,0]*=1.3;knees[:,0]*=1.3;head=np.array([.02*s,-.08*q,0.])
  arms=np.array([[-55,165,30],[55,165,30],[-86,186,0],[86,186,0]])
 elif name=='snap_sway':
  # Finger snaps at the shoulders, alternating sides on the backbeat.
  root=np.array([28*s,3*pulse,0.]);body=np.array([0.,.08*slow,.06*s]);head=np.array([0.,0.,.06*s])
  for i,side in enumerate([-1,1]):
   lift=max(0,-side*s);feet[i]=[side*(36+10*lift),12+12*lift,6];knees[i]=[side*(27+5*lift),80+6*lift,12]
  arms=np.array([[-78,240+18*max(0,-s),50],[78,240+18*max(0,s),50],[-80,200,15],[80,200,15]])
 elif name=='twist':
  root=np.array([18*s,-8*pulse,0.]);body=np.array([.03,.58*s,.025*s]);head[1]=-.3*s
  knees[:,0]+=[15*s,15*s];feet[:,0]+=[-11*s,-11*s]
  arms=np.array([[-71,241+22*c,58],[71,241-22*c,58],[-80,190,12],[80,190,12]])
 elif name=='tracking_turn':
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

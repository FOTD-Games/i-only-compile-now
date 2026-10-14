"""Map data/timeline.json onto a new recording's section boundaries.

Every event time is moved piecewise-linearly between the old and new section starts
(`anchors`), so a cut 40% of the way through Verse 2 stays 40% of the way through it.
Drum-snapped chorus cuts re-snap at render time. Sections are matched by name, in
order; one the new recording skips (e.g. a dropped chorus) collapses to zero length,
taking its shots and per-chorus camera/light entries with it. Review the result: a
swing arrangement phrases differently, so expect to nudge a few cuts by hand.

usage: python src/retime.py [--cues data/cues.json] [--duration SECONDS] [--dry-run]
"""
from pathlib import Path
import argparse, bisect, json, subprocess

ROOT=Path(__file__).resolve().parents[1]
SKIP={'song','anchors','prominence','height'}

CHORUS_NAMES={'Chorus','Final Chorus'}

def section_starts(cues):
 # The coda is not part of the upstream structure; it gets its own block below.
 cues=[c for c in cues if c['section']!='Coda'];out=[]
 for i,c in enumerate(cues):
  if i==0 or c['section']!=cues[i-1]['section']:out.append((c['section'],round(float(c['start']),3)))
 return out

def match_sections(old_names,new):
 # Greedy in-order match; an old section with no counterpart collapses onto the next match.
 j=0;starts=[None]*len(old_names)
 for i,name in enumerate(old_names):
  if j<len(new) and new[j][0]==name:starts[i]=new[j][1];j+=1
 assert j==len(new),f'new sections not in the old order: {[n for n,_ in new[j:]]}'
 return starts

def mapper(old,new):
 assert len(old)==len(new),f'section count changed: {len(old)} -> {len(new)}'
 def f(t):
  i=min(len(old)-2,max(0,bisect.bisect_right(old,t)-1))
  a,b,c,d=old[i],old[i+1],new[i],new[i+1]
  return round(c+(t-a)*(d-c)/(b-a),4)
 return f

def walk(node,f,key=None):
 if key in SKIP:return node
 if isinstance(node,dict):return {k:walk(v,f,k) for k,v in node.items()}
 if isinstance(node,list):return [walk(v,f,key) for v in node]
 if isinstance(node,(int,float)) and not isinstance(node,bool):return f(node)
 return node

def main():
 ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
 ap.add_argument('--cues',type=Path,default=ROOT/'data/source-cues.json')
 ap.add_argument('--duration',type=float,help='new song length; default: ffprobe the timeline audio')
 ap.add_argument('--dry-run',action='store_true')
 args=ap.parse_args()
 path=ROOT/'data/timeline.json';T=json.loads(path.read_text())
 duration=args.duration or float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(ROOT/T['song']['audio'])],capture_output=True,text=True,check=True).stdout)
 cues=json.loads(args.cues.read_text());coda=[c for c in cues if c['section']=='Coda']
 # With a coda, the desk pullback runs on through the band's tail and fades out
 # 2.5 s before the first voice, leaving a short dark beat before her spotlight.
 outro_end=round(coda[0]['start']-2.5,3) if coda else round(duration,3)
 found=section_starts(cues);names=T['sections'];matched=match_sections(names,found)
 for i in range(len(matched)-1,-1,-1):
  if matched[i] is None:matched[i]=matched[i+1] if i+1<len(matched) else outro_end
 new=[0.0]+matched+[outro_end]
 old=T['anchors'][:-1]+[T.get('coda',{}).get('start',T['anchors'][-1])]
 f=mapper(old,new)
 out=walk({k:v for k,v in T.items() if k!='coda'},f)
 # Drop per-chorus entries for any chorus the recording skipped, and renumber the rest.
 choruses=[i for i,n in enumerate(names) if n in CHORUS_NAMES]
 kept=[k for k,i in enumerate(choruses) if any(n==names[i] and s==matched[i] for n,s in found)]
 renum={old_k:new_k for new_k,old_k in enumerate(kept)}
 for key in ['cameras','light_start']:out['chorus'][key]=[out['chorus'][key][k] for k in kept]
 shots=[]
 for shot in out['shots']:
  if isinstance(shot[0],str):
   k=int(shot[0][6:])
   if k not in renum:continue
   shot=[f'chorus{renum[k]}',*shot[1:]]
  shots.append(shot)
 # Shots squeezed to zero length by a collapsed section are dropped.
 out['shots']=[s for s,n in zip(shots,shots[1:]+[None]) if n is None or isinstance(s[0],str) or isinstance(n[0],str) or s[0]<n[0]]
 out['sections']=[n for n,_ in found];out['anchors']=[0.0]+[s for _,s in found]+[outro_end]
 out['song']={**T['song'],'duration':round(duration,3)}
 if coda:
  # Three voices: one per coda line, or the later two staggered on the second phrase.
  e=[round(c['start'],3) for c in coda][:3]
  while len(e)<3:e.append(round(e[-1]+1.8,3))
  out['coda']=dict(start=outro_end,entries=e)
 for n,a,b in zip(['start']+names+['end'],old,new):print(f'{n:13} {a:9.3f} -> {b:9.3f}')
 if coda:print('coda',out['coda'])
 if not args.dry_run:
  # One line per shot keeps the file reviewable in diffs.
  text=json.dumps({k:v for k,v in out.items() if k!='shots'},indent=1)[:-2]
  text+=',\n "shots": [\n'+',\n'.join('  '+json.dumps(s) for s in out['shots'])+'\n ]\n}\n'
  path.write_text(text);print('wrote',path)
  write_chapters(out,cues)

def write_chapters(T,cues):
 # Two opening chapters for the listing and the desk, then one per sung section.
 marks=[(0,'Printer listing'),(T['intro']['desk'],'At the desk')]
 for i,c in enumerate(cues):
  if i==0 or c['section']!=cues[i-1]['section']:marks.append((T['intro']['perform'] if i==0 else c['start'],c['section']))
 if 'coda' in T:marks[-1]=(T['coda']['start'],'Coda')
 ends=[m[0] for m in marks[1:]]+[T['song']['duration']]
 text=f";FFMETADATA1\ntitle={T['song']['title']}\ncomment=Low-poly 1960 supper-club performance\n"
 for (start,title),end in zip(marks,ends):text+=f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={round(start*1000)}\nEND={round(end*1000)}\ntitle={title}\n"
 (ROOT/'data/chapters.ffmeta').write_text(text);print('wrote chapters.ffmeta')

if __name__=='__main__':main()

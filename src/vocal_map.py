"""Print where the separated vocal is active, to help pick section start times.

Run after prepare_vocals.py. Phrases separated by more than --gap seconds of
silence are printed on their own line; section starts are usually after the
longer gaps (instrumental breaks, horn solos).

usage: python src/vocal_map.py [--gap 0.8]
"""
from pathlib import Path
import argparse, os
import numpy as np
from scipy.ndimage import uniform_filter1d

ROOT=Path(__file__).resolve().parents[1]
WORK=Path(os.environ.get('IDCA_WORK_DIR',str(ROOT/'work')))

def main():
 ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
 ap.add_argument('--gap',type=float,default=.8)
 args=ap.parse_args()
 x=np.load(WORK/'vocals16.npy');sr=16000
 rms=np.sqrt(uniform_filter1d(x*x,size=sr//20))[::sr//100]
 active=rms>max(np.percentile(rms,90)*.12,1e-4)
 spans=[];start=None
 for i,v in enumerate(active):
  if v and start is None:start=i
  if not v and start is not None:spans.append([start/100,i/100]);start=None
 if start is not None:spans.append([start/100,len(active)/100])
 merged=[]
 for a,b in spans:
  if merged and a-merged[-1][1]<args.gap:merged[-1][1]=b
  elif b-a>=.25:merged.append([a,b])
 prev=0
 for a,b in merged:
  print(f'{a:8.2f} - {b:8.2f}  ({b-a:5.1f}s)   gap before {a-prev:5.1f}s');prev=b

if __name__=='__main__':main()

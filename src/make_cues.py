"""Build data/source-cues.json from a lyrics file and rough section start times.

align_vocals.py only needs each section's start to within a couple of seconds; it
rebuilds every cue time from the sung words. Pass one start per [Section] header,
in order (repeated section names each get their own start).

Bracket tags that are not section names (e.g. "[Female backing harmonies]",
"[male lead]") set who sings the following lines; the renderer opens only that
character's mouth. Section headers may carry a singer too ("[Verse 1: Male Lead Solo]").

usage: python src/make_cues.py lyrics-1960.txt 14.2 42.0 51.5 ... [--end SECONDS]
"""
from pathlib import Path
import argparse, json, re

ROOT=Path(__file__).resolve().parents[1]

SECTION=re.compile(r'(Final Chorus|Pre-Chorus|Chorus|Verse \d+|Bridge|Outro|Coda|Intro)\b',re.I)

def singer(tag):
 tag=tag.lower()
 if 'female' in tag and 'male lead' not in tag:return 'backing'
 if 'male' in tag:return 'lead'
 return None

def sections(path):
 out=[];who='lead'
 for line in Path(path).read_text().splitlines():
  line=line.strip()
  if not line:continue
  m=re.fullmatch(r'\[(.+)\]',line)
  if m:
   tag=m.group(1);sec=SECTION.match(tag)
   if sec:
    name=sec.group(1).title()
    out.append((name,[]));who=singer(tag) or ('backing' if name=='Coda' else 'lead')
   else:who=singer(tag) or who
  else:
   # Tags can also sit inside a line ("And Daisy? [female backing harmony] Daisy,"):
   # each piece becomes its own cue with its own singer.
   for k,piece in enumerate(re.split(r'(\[[^\]]+\])',line)):
    if k%2:who=singer(piece[1:-1]) or who
    elif piece.strip():out[-1][1].append((piece.strip().replace('*',''),who))
 return out

def main():
 ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
 ap.add_argument('lyrics');ap.add_argument('starts',type=float,nargs='+')
 ap.add_argument('--end',type=float,help='end of the last section (default: last start + 20 s)')
 args=ap.parse_args()
 secs=sections(args.lyrics)
 if len(secs)!=len(args.starts):
  ap.error(f'{len(secs)} sections ('+', '.join(n for n,_ in secs)+f') but {len(args.starts)} starts')
 if sorted(args.starts)!=args.starts:ap.error('starts must increase')
 bounds=args.starts+[args.end or args.starts[-1]+20]
 cues=[]
 for (name,lines),a,b in zip(secs,bounds,bounds[1:]):
  # Spread lines evenly as placeholders; only the section start is used for alignment.
  step=(b-a)/len(lines)
  cues+=[dict(start=round(a+i*step,3),end=round(a+(i+1)*step,3),text=text,section=name,singer=who) for i,(text,who) in enumerate(lines)]
 dest=ROOT/'data/source-cues.json';dest.write_text(json.dumps(cues,indent=2,ensure_ascii=False)+'\n')
 print(f'wrote {len(cues)} cues in {len(secs)} sections to {dest}')

if __name__=='__main__':main()

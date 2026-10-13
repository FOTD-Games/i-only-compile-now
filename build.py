#!/usr/bin/env python3
"""Render the complete video, a preview, or a still from the saved vocal timing."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import argparse, json, os, shutil, subprocess, sys

ROOT=Path(__file__).resolve().parent
DURATION=198.76

def timestamp(t):
    ms=round(t*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'

def write_captions(destination):
    cues=json.loads((ROOT/'data/cues.json').read_text())
    destination.write_text('\n\n'.join(f"{i+1}\n{timestamp(c['start'])} --> {timestamp(c['end'])}\n{c['text']}" for i,c in enumerate(cues))+'\n',encoding='utf-8')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start',type=float,default=0)
    parser.add_argument('--end',type=float,default=DURATION)
    parser.add_argument('--still',type=float)
    parser.add_argument('--workers',type=int,default=3)
    parser.add_argument('--output-dir',type=Path,default=ROOT/'renders')
    args=parser.parse_args()
    if not 0<=args.start<args.end<=DURATION:parser.error('Require 0 <= start < end <= 198.76')
    if args.still is not None and not 0<=args.still<DURATION:parser.error('Invalid still time')
    if not 1<=args.workers<=8:parser.error('Choose 1–8 workers')
    if not shutil.which('ffmpeg'):parser.error('Install FFmpeg and add it to PATH')
    work=Path(os.environ.get('IDCA_WORK_DIR',str(ROOT/'work'))).resolve();work.mkdir(parents=True,exist_ok=True)
    out=args.output_dir.resolve();out.mkdir(parents=True,exist_ok=True)
    env={**os.environ,'IDCA_WORK_DIR':str(work)}
    if args.still is not None:
        os.environ['IDCA_WORK_DIR']=str(work)
        sys.path.insert(0,str(ROOT/'src'))
        import render_video
        dest=out/f'frame-{args.still:g}.jpg';render_video.render(args.still).save(dest,quality=95);print(dest);return
    first,last=round(args.start*30),round(args.end*30)
    if last<=first:parser.error('Select at least one frame')
    workers=min(args.workers,last-first)
    bounds=[first+round((last-first)*i/workers) for i in range(workers+1)]
    parts=[work/f'part-{i}.mp4' for i in range(workers)]
    def render(i):
        subprocess.run([sys.executable,str(ROOT/'src/render_video.py'),'segment',str(bounds[i]/30),str(bounds[i+1]/30),str(parts[i])],env=env,check=True)
    with ThreadPoolExecutor(max_workers=workers) as pool:list(pool.map(render,range(workers)))
    listing=work/'concat.txt';listing.write_text(''.join(f"file '{p.name}'\n" for p in parts))
    full=first==0 and last==round(DURATION*30)
    stem='I-Dont-Code-Anymore-music-video' if full else f'preview-{first/30:g}-{last/30:g}'
    dest=out/f'{stem}.mp4'
    cmd=['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',str(listing),'-ss',str(first/30),'-i',str(ROOT/"assets/I Don't Code Anymore.m4a")]
    if full:cmd+=['-i',str(ROOT/'data/chapters.ffmeta')]
    cmd+=['-map','0:v:0','-map','1:a:0','-map_metadata','2' if full else '-1','-map_chapters','2' if full else '-1','-c:v','copy','-c:a','aac','-b:a','192k','-t',str(min(DURATION,args.end)-first/30),'-movflags','+faststart',str(dest)]
    subprocess.run(cmd,check=True)
    if full:write_captions(out/'I-Dont-Code-Anymore.srt')
    print(dest)

if __name__=='__main__':main()

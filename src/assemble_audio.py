"""Join the song and the a cappella coda into the one track the video plays.

The coda recording (assets/Outro.wav) came back from Suno with accompaniment, so
Demucs keeps only its vocals. The song plays out, then a short silence, then the
women alone.

usage: python src/assemble_audio.py [--gap 2.0] [--keep-music]
"""
from pathlib import Path
import argparse, os, subprocess, wave
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
WORK=Path(os.environ.get('IDCA_WORK_DIR',str(ROOT/'work')));WORK.mkdir(parents=True,exist_ok=True)
SONG=ROOT/'assets/I Only Compile Now.wav';CODA=ROOT/'assets/Outro.wav'
OUT=ROOT/'assets/I-Only-Compile-Now-full.wav';SR=48000

def read(path):
 tmp=WORK/(path.stem+'-48k.wav')
 subprocess.run(['ffmpeg','-y','-v','error','-i',str(path),'-ar',str(SR),'-ac','2','-c:a','pcm_s16le',str(tmp)],check=True)
 with wave.open(str(tmp)) as f:return np.frombuffer(f.readframes(f.getnframes()),np.int16).reshape(-1,2).T.astype(np.float32)/32768

def coda_vocals(mix):
 import torch,torchaudio
 from demucs.pretrained import get_model
 from demucs.apply import apply_model
 torch.hub.set_dir(str(WORK/'model-cache'));torch.set_num_threads(4)
 model=get_model('htdemucs').cpu().eval()
 x=torchaudio.functional.resample(torch.from_numpy(mix),SR,model.samplerate)
 ref=x.mean(0);mean,std=ref.mean(),ref.std()
 with torch.inference_mode():out=apply_model(model,((x-mean)/std)[None],device='cpu',shifts=1,split=True,overlap=.25,num_workers=0)[0]
 vocals=out[model.sources.index('vocals')]*std+mean
 return torchaudio.functional.resample(vocals,model.samplerate,SR).numpy()

def main():
 ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
 ap.add_argument('--gap',type=float,default=2.0,help='seconds of silence after the band stops')
 ap.add_argument('--keep-music',action='store_true',help='use the coda as recorded')
 args=ap.parse_args()
 song=read(SONG);coda=read(CODA)
 if not args.keep_music:coda=coda_vocals(coda)
 # Short fades so the separated stem neither clicks in nor cuts off.
 fade=np.ones(coda.shape[1],np.float32);n=int(.03*SR);fade[:n]=np.linspace(0,1,n);fade[-int(.4*SR):]=np.linspace(1,0,int(.4*SR))
 full=np.concatenate([song,np.zeros((2,int(args.gap*SR)),np.float32),coda*fade],axis=1)
 with wave.open(str(OUT),'wb') as w:
  w.setnchannels(2);w.setsampwidth(2);w.setframerate(SR)
  w.writeframes((np.clip(full,-1,1).T*32767).astype(np.int16).tobytes())
 print(f'{OUT.name}: song {song.shape[1]/SR:.2f}s + gap {args.gap}s + coda {coda.shape[1]/SR:.2f}s; coda starts at {(song.shape[1]/SR+args.gap):.2f}s')

if __name__=='__main__':main()

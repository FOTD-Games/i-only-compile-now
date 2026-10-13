"""Measure drum attacks directly; never fill a percussion gap with a tempo grid."""
from pathlib import Path
import json,os,subprocess,wave
import numpy as np
from scipy.signal import stft,resample_poly,find_peaks

ROOT=Path(__file__).resolve().parents[1]
WORK=Path(os.environ.get('IDCA_WORK_DIR',str(ROOT/'work')));WORK.mkdir(parents=True,exist_ok=True)
stem=WORK/'drums441.npy'
if not stem.exists():
 import torch
 from demucs.pretrained import get_model
 from demucs.apply import apply_model
 torch.hub.set_dir(str(WORK/'model-cache'));torch.set_num_threads(6)
 model=get_model('htdemucs').cpu().eval()
 wav=WORK/'mix441.wav'
 subprocess.run(['ffmpeg','-y','-v','error','-i',str(ROOT/"assets/I Don't Code Anymore.m4a"),'-vn','-sn','-ar','44100','-ac','2',str(wav)],check=True)
 with wave.open(str(wav)) as f:data=np.frombuffer(f.readframes(f.getnframes()),np.int16).reshape(-1,2).T.copy().astype(np.float32)/32768
 mix=torch.from_numpy(data);ref=mix.mean(0);mean=ref.mean();std=ref.std()
 with torch.inference_mode():out=apply_model(model,((mix-mean)/std)[None],device='cpu',shifts=0,split=True,overlap=.1,progress=True,num_workers=0)[0]
 drums=out[model.sources.index('drums')]*std+mean
 np.save(stem,drums.mean(0).numpy())
x=resample_poly(np.load(stem),160,441)
f,t,z=stft(x,16000,nperseg=768,noverlap=688,boundary='zeros')
mag=np.abs(z);flux=np.maximum(np.diff(mag,axis=1,prepend=mag[:,:1]),0)
score=flux[(f>=35)&(f<=260)].sum(0)+.2*flux[(f>=1000)&(f<=7000)].sum(0)
score/=np.percentile(score,99)
peaks,_=find_peaks(score,distance=64,prominence=.25,height=.45)
detected=[round(float(t[i]),4) for i in peaks]
# Retain the opening bass downbeat measured from the full mix in the original edit.
# This one accent is absent from the separated drum stem.
beats=sorted(set(detected+[53.1]))
info=dict(method='Spectral-flux attacks in isolated htdemucs drums; no extrapolated beats',
          resolution_seconds=.005,min_peak_separation_seconds=.32,
          mix_downbeat_anchors=[53.1],detected_drum_beats=detected,beats=beats)
(ROOT/'data/percussion-beats.json').write_text(json.dumps(info,indent=2)+'\n')
np.savez(WORK/'drum-onsets.npz',time=t,score=score)
print(f'Saved {len(beats)} measured percussion events.')

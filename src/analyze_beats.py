from pathlib import Path
import wave,json,os,subprocess
import numpy as np
from scipy.signal import stft,find_peaks
p=Path(__file__).resolve().parents[1]
w=Path(os.environ.get('IDCA_WORK_DIR',str(p/'work')));w.mkdir(parents=True,exist_ok=True)
subprocess.run(['ffmpeg','-y','-v','error','-i',str(p/"assets/I Don't Code Anymore.m4a"),'-vn','-sn','-ar','16000','-ac','1','-c:a','pcm_s16le',str(w/'original-audio.wav')],check=True)
with wave.open(str(w/'original-audio.wav')) as f:x=np.frombuffer(f.readframes(f.getnframes()),np.int16).astype(float)/32768;sr=f.getframerate()
f,t,Z=stft(x,sr,nperseg=1024,noverlap=864,boundary='zeros');mag=np.abs(Z)
bass=(f>35)&(f<190);snare=(f>1200)&(f<6500)
flux=np.maximum(np.diff(mag,axis=1,prepend=mag[:,:1]),0)
onset=flux[bass].sum(0)+.20*flux[snare].sum(0)
onset/=np.percentile(onset,99)
# Estimate tempo and phase from the steady chorus rhythm, not the vocal syllables.
sel=(t>=53)&(t<115);tt=t[sel];oo=onset[sel]
best=(-1,None,None)
for period in np.linspace(.41,.46,501):
 for phase in np.linspace(0,period,50,endpoint=False):
  b=53+phase+np.arange(int(62/period)+1)*period
  score=np.interp(b,tt,oo,left=0,right=0).mean()
  if score>best[0]:best=(score,period,phase)
score,period,phase=best
print('Fit',score,'bpm',60/period,'first',53+phase)
peaks,_=find_peaks(onset,distance=22,prominence=.16)
print('Onsets 51–57:',[(round(float(t[i]),3),round(float(onset[i]),2)) for i in peaks if 51<t[i]<57])
# Follow nearby measured transients to accommodate slight timing variation.
beats=[]
for expected in np.arange(53+phase,198.76,period):
 nearby=peaks[abs(t[peaks]-expected)<.08]
 actual=float(t[nearby[np.argmax(onset[nearby])]]) if len(nearby) else float(expected)
 beats.append(round(actual,4))
info={'start':53.0,'estimated_bpm':60/period,'period':period,'method':'low-frequency and broadband spectral-flux onsets, regular beat grid with local transient refinement','beats':beats}
(p/'data/beats.json').write_text(json.dumps(info,indent=2)+'\n')
np.savez(w/'beat-analysis.npz',time=t,onset=onset)

"""Song-specific timing and identity, loaded from data/timeline.json.

Every scene boundary, chorus camera cut and lighting start lives in that file, so a
new recording only needs a retimed timeline (see src/retime.py), not code edits.
"""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
T=json.loads((ROOT/'data/timeline.json').read_text())
SONG=T['song']
DURATION=SONG['duration']
AUDIO=ROOT/SONG['audio']

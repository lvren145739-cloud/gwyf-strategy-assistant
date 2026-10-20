from pathlib import Path
import sys
import hashlib
import json
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
import cv2,numpy,mss,webview
from recognizer import Recognizer
info=json.loads((root/'models/model-card.json').read_text('utf-8'))
for name,expected in info['files'].items():
    actual=hashlib.sha256((root/'models'/name).read_bytes()).hexdigest()
    if actual!=expected['sha256']:
        raise RuntimeError('Model integrity check failed: '+name)
r=Recognizer()
import numpy as np
for session in (r.rank,r.suit):
    assert np.isfinite(session.run(None,{'image':np.zeros((1,1,64,64),np.float32)})[0]).all()
assert np.isfinite(r.card.run(None,{'image':np.zeros((1,3,96,64),np.float32)})[0]).all()
assert np.isfinite(r.recovery_glyph.run(None,{'image':np.zeros((1,1,64,64),np.float32)})[0]).all()
assert np.isfinite(r.recovery_rank.run(None,{'image':np.zeros((1,1,48,48),np.float32)})[0]).all()
print('OK: models loaded on CPU. No GPU or cloud service needed.')
print('Python',sys.version.split()[0],'OpenCV',cv2.__version__,'NumPy',numpy.__version__,r.backend)

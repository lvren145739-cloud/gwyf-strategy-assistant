"""Early geometry audit uses V3 verifier + explicitly labelled OLD glyph heads.
Temporary development helper, not a comparison of the final V3 glyph model.
"""
from pathlib import Path
import sys,json,cv2,numpy as np,importlib.util
r=Path(__file__).resolve().parents[1];sys.path.insert(0,str(r))
from recognizer import Recognizer,DNNSession
class OldGlyphAdapter:
 def __init__(self):self.rank=DNNSession(r.parent/'vision-window-fix/models/rank.onnx');self.suit=DNNSession(r.parent/'vision-window-fix/models/suit.onnx')
 def predict(self,x):
  x=np.stack([cv2.resize(a[0],(48,48)) for a in x])[:,None]
  return np.concatenate([self.rank.run(None,{'image':x})[0],self.suit.run(None,{'image':x})[0]],axis=1)
a=Recognizer.__new__(Recognizer);a.card=DNNSession(r/'models/card.onnx');a.glyph=OldGlyphAdapter()
cases=json.loads((r/'tests/model-comparison.json').read_text())['cases'];out=[]
for c in cases:
 im=cv2.imread(str(r/'research'/c['file']));o=a.read(im,c['regions'],c['mode']);o.pop('recognitionMs',None)
 for card in o['cards']:card.pop('preview',None)
 print(c['name'],[(x['role'],x['rank'],x['suit'],x['faceDown'],x['review'],round(x['cardScore'],3),x['issues']) for x in o['cards']],o['warnings'],flush=True)
 out.append({'name':c['name'],**o})
(r/'research/v3-data/early-geometry.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
for file in ['full-240.jpg','full-1435.jpg','full-2024.jpg','full-2066.jpg']:
 im=cv2.imread(str(r/'research'/file));o=a.read(im,{},'poker' if file in ['full-2024.jpg','full-2066.jpg'] else 'blackjack')
 print('AUTO',file,[(x['role'],x['rank'],x['suit'],x['faceDown'],x['review'],round(x['cardScore'],2)) for x in o['cards']],o['warnings'],o['recognitionMs'],flush=True)

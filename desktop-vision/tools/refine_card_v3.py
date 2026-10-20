"""Fine-tune the full-card verifier on reviewed multi-scale hard negatives."""
from pathlib import Path
import sys,json,time,hashlib
r=Path(__file__).resolve().parents[1];sys.path.insert(0,str(r/'tools'))
import train_v3 as t
import torch,cv2
# One CPU thread leaves the two-thread glyph training responsive.
torch.set_num_threads(1)
recs=t.records();pos,neg=t.base_cards(recs)
for c in json.loads((r/'training/v3-hard-negatives.json').read_text()):
 # Avoid possibly unread cards inside an already reviewed real hand's band.
 # The large majority of these are UI keys, characters and floor fragments.
 im=cv2.imread(str(r/'research'/c['file']));neg.append(im)
model=t.CardNetV3();model.load_state_dict(torch.load(r/'research/v3-data/card-v3.pt',weights_only=True))
x,y=t.verifier_data(pos,neg)
info=t.train(model,x,y,'card',12)
info.update(stage='hard-negative refinement',reviewedBackgrounds=len(neg),time=time.time())
p=r/'models/card.onnx';info.update(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
(r/'training/v3-card-refinement.json').write_text(json.dumps(info,indent=2))
print('CARD REFINEMENT COMPLETE',flush=True)

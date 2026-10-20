"""Targeted open-top 4 refinement with balanced old-class replay.
Only a manually reviewed gameplay crop is added, never an inferred label.
"""
from pathlib import Path
import sys,json,random,time,hashlib
import numpy as np,cv2,torch,onnx
from torch import nn
from onnx import numpy_helper
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tools'))
import train_v3 as t
from train_v2 import GlyphNetV2
from recognizer import normalise_glyph
D=ROOT/'research/v031-data';D.mkdir(exist_ok=True)
random.seed(3311);np.random.seed(3311);torch.manual_seed(3311);torch.set_num_threads(2)
frame=cv2.imread(str(ROOT/'research/bili-cards/023.jpg'))
quad=np.float32([[326,337],[353,434],[160,489],[155,387]])
m=cv2.getPerspectiveTransform(quad,np.float32([[0,0],[143,0],[143,191],[0,191]]))
card=cv2.warpPerspective(frame,m,(144,192));cv2.imwrite(str(D/'reviewed-four-hearts.png'),card)
real=[normalise_glyph(card[:76,:65],clean_border=True),normalise_glyph(card[:82,:69],clean_border=True)]
procedural=[]
for _ in range(70):
 a=np.zeros((90,75),np.uint8);left=random.randint(12,22);right=random.randint(43,57);top=random.randint(6,16);bar=random.randint(38,54);bottom=random.randint(70,83);thick=random.randint(3,7)
 cv2.line(a,(left,top),(left+random.randint(-2,4),bar),255,thick,cv2.LINE_AA)
 cv2.line(a,(left,bar),(right+random.randint(0,5),bar),255,thick,cv2.LINE_AA)
 cv2.line(a,(right,top),(right+random.randint(-2,2),bottom),255,thick,cv2.LINE_AA)
 procedural.append(normalise_glyph(255-a))
pos,neg=t.base_cards(t.records());x,y,_=t.glyph_data(pos,neg)
# Keep every class, including UNKNOWN and all suits, in each refinement epoch.
ids=[]
for rank in range(15):
 subset=torch.where((y[:,0]==rank)&(y[:,1]==4))[0];ids.extend(subset[torch.randperm(len(subset))[:150]].tolist())
for suit in range(4):
 subset=torch.where(y[:,1]==suit)[0];ids.extend(subset[torch.randperm(len(subset))[:110]].tolist())
xs=[a[0].numpy() for a in x[ids]];ys=y[ids].tolist()
for i in range(430):
 base=random.choice(real if random.random()<.60 else procedural)
 xs.append(t.aug_mask(base));ys.append([3,4])
for i in range(100):
 base=np.rot90(random.choice(real),random.choice([1,2,3])).copy()
 xs.append(t.aug_mask(base));ys.append([14,4])
x=torch.from_numpy(np.stack(xs))[:,None];y=torch.tensor(ys)
model=t.GlyphNetV3();model.load_state_dict(torch.load(ROOT/'research/v3-data/glyph-v3.pt',weights_only=True))
# Keep early filters stable; refine higher features and classification layers.
for module in list(model.net.children())[:16]:
 for p in module.parameters():p.requires_grad=False
opt=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=.00017,weight_decay=.005)
start=time.perf_counter();losses=[]
for epoch in range(6):
 model.train()
 for module in list(model.net.children())[:16]:module.eval()
 total=0
 for batch in torch.randperm(len(y)).split(96):
  out=model(x[batch]);target=y[batch];loss=nn.functional.cross_entropy(out[:,:15],target[:,0],label_smoothing=.005)+nn.functional.cross_entropy(out[:,15:],target[:,1],label_smoothing=.005)
  opt.zero_grad();loss.backward();nn.utils.clip_grad_norm_(model.parameters(),4);opt.step();total+=float(loss.detach())*len(batch)
 losses.append(round(total/len(y),5));print('shared glyph',epoch+1,losses[-1],round(time.perf_counter()-start,1),flush=True)
model.eval();torch.onnx.export(model,x[:1],str(ROOT/'models/glyph-open.onnx'),input_names=['image'],output_names=['logits'],opset_version=17,dynamic_axes={'image':{0:'batch'},'logits':{0:'batch'}});torch.save(model.state_dict(),D/'glyph-v031.pt')
# Independent small rank head: recover original weights from its own ONNX graph.
legacy=GlyphNetV2(15);legacy.load_state_dict({p.name:torch.from_numpy(numpy_helper.to_array(p).copy()) for p in onnx.load(str(ROOT/'models/rank-v2.onnx')).graph.initializer})
small=torch.from_numpy(np.stack([cv2.resize(a[0].numpy(),(48,48)) for a in x]))[:,None]
opt=torch.optim.AdamW(legacy.parameters(),lr=.00025,weight_decay=.005);legacy_losses=[]
for epoch in range(9):
 legacy.train();total=0
 for batch in torch.randperm(len(y)).split(128):
  out=legacy(small[batch]);loss=nn.functional.cross_entropy(out,y[batch,0],label_smoothing=.005)
  opt.zero_grad();loss.backward();nn.utils.clip_grad_norm_(legacy.parameters(),4);opt.step();total+=float(loss.detach())*len(batch)
 legacy_losses.append(round(total/len(y),5));print('independent rank',epoch+1,legacy_losses[-1],flush=True)
legacy.eval();torch.onnx.export(legacy,small[:1],str(ROOT/'models/rank-open.onnx'),input_names=['image'],output_names=['logits'],opset_version=17,dynamic_axes={'image':{0:'batch'},'logits':{0:'batch'}})
meta=json.loads((ROOT/'models/model-card.json').read_text());meta['version']='0.3.1';meta['openFourRefinement']={'source':'bili-cards/023.jpg','quad':quad.tolist(),'rank':'4','suit':'hearts','reviewedAdditionalPhysicalHands':1,'sharedEpochs':6,'independentEpochs':9,'examples':len(y),'sharedLoss':losses,'independentLoss':legacy_losses,'seconds':round(time.perf_counter()-start,1),'replay':'all rank/suit classes, UNKNOWN and rotated open fours; no selected holdout frame used'}
for name in ['glyph-open.onnx','rank-open.onnx']:
 p=ROOT/'models'/name;meta['files'][name]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
(ROOT/'models/model-card.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2));(ROOT/'training/v031-refinement.json').write_text(json.dumps(meta['openFourRefinement'],indent=2));print('REFINEMENT COMPLETE',flush=True)

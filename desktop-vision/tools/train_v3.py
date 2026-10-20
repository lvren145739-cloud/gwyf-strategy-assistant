"""V3 shared glyph CNN and full-card verifier, trained locally on CPU.
Source frames are research-only. Evaluation hands/negative video are excluded.
"""
from pathlib import Path
import json,sys,random,time,hashlib,importlib.util
import cv2,numpy as np
from PIL import Image,ImageDraw,ImageFont
import torch
from torch import nn
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'research';D=R/'v3-data'
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tools'))
# Freeze V2 crop normalization for the training input; runtime V3 uses the same
# masks, then scales to 64px. Geometry proposals are upgraded independently.
spec=importlib.util.spec_from_file_location('legacy',str(ROOT.parent/'vision-window-fix/recognizer.py'));legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
from training_primitives import draw_suit
SEED=3301;random.seed(SEED);np.random.seed(SEED);torch.manual_seed(SEED);torch.set_num_threads(2);cv2.setNumThreads(1)
RANKS=legacy.RANKS
class GlyphNetV3(nn.Module):
 def __init__(self):
  super().__init__();layers=[];prev=1
  for c in [24,48,96,128]:
   layers += [nn.Conv2d(prev,c,3,padding=1),nn.BatchNorm2d(c),nn.ReLU(),nn.Conv2d(c,c,3,padding=1),nn.BatchNorm2d(c),nn.ReLU(),nn.MaxPool2d(2)];prev=c
  self.net=nn.Sequential(*layers,nn.Flatten(),nn.Linear(128*4*4,192),nn.ReLU(),nn.Dropout(.18),nn.Linear(192,20))
 def forward(self,x):return self.net(x)
class CardNetV3(nn.Module):
 def __init__(self):
  super().__init__();layers=[];prev=3
  for c in [16,32,64]:
   layers += [nn.Conv2d(prev,c,3,padding=1),nn.BatchNorm2d(c),nn.ReLU(),nn.Conv2d(c,c,3,padding=1),nn.BatchNorm2d(c),nn.ReLU(),nn.MaxPool2d(2)];prev=c
  self.net=nn.Sequential(*layers,nn.Flatten(),nn.Linear(64*12*8,128),nn.ReLU(),nn.Dropout(.2),nn.Linear(128,3))
 def forward(self,x):return self.net(x)

def records():
 old=json.loads((D/'reviewed-initial.json').read_text());extra=json.loads((D/'extra-candidates.json').read_text())
 labels={55:('K',0,1),56:('9',0,1),65:('6',3,1),66:('8',1,1),67:('Q',1,1),68:('Q',0,1),69:('Q',3,1),70:('6',2,1),83:('5',2,1),84:('9',2,1),85:('10',1,1),98:('Q',0,1),99:('6',0,1)}
 ignore={0,3,4,5,10,16,17,18,19,25,32,35,36,37,39,40,41,49,57,61,77,86,87,92,100,101,105,110,111,112,122,123,128,136,140,141,142,143,144,145,151}
 for i,c in enumerate(extra):
  c=dict(c)
  if i in labels:
   rank,suit,k=labels[i];c.update(label='face',rank=rank,suit=suit,rotation=k,split='holdout-angle' if i in [83,84,85] else 'train')
  elif i in ignore:c.update(label='ignore',split='ignore')
  else:c.update(label='background',split='train')
  old.append(c)
 # Do not train on any neighbouring frame of the held-out new poker hand.
 for c in old:
  if c['frame'].startswith('v3-frames/long-2075') or c['frame'].startswith('v3-frames/long-2082'):c['split']='holdout-hand'
 return old

def base_cards(recs):
 positive=[];negative=[]
 for c in recs:
  if c['split']!='train' or c['label']=='ignore':continue
  im=cv2.imread(str(R/c['file']))
  if c['label']=='background':negative.append(im)
  else:
   im=cv2.resize(np.rot90(im,c.get('rotation',0)).copy(),(96,128))
   positive.append((im,c['rank'],c['suit'],c['id']))
 # Include the previously reviewed bases; their original PNGs are unchanged.
 for key,(rank,suit) in json.loads((ROOT/'training/v01-training-records.json').read_text()).items():
  p=R/(key+'.png') if key.startswith('fullcard-') else R/'cards'/(key+'.png')
  positive.append((cv2.imread(str(p)),rank,suit,key))
 return positive,negative

def aug_mask(im):
 im=cv2.resize(im,(64,64));m=cv2.getRotationMatrix2D((32,32),random.uniform(-20,20),random.uniform(.65,1.16));m[0,1]+=random.uniform(-.22,.22);m[:,2]+=np.random.uniform(-3.5,3.5,2)
 out=cv2.warpAffine(im,m,(64,64))
 if random.random()<.3:out=(cv2.erode if random.random()<.5 else cv2.dilate)(out,np.ones((2,2),np.uint8))
 if random.random()<.45:
  k=random.randint(15,44);out=cv2.resize(cv2.resize(out,(k,k)),(64,64))
 if random.random()<.25:out=cv2.GaussianBlur(out,(3,3),random.uniform(.3,1))
 return np.clip(out.astype(np.float32)/255*random.uniform(.75,1)+np.random.normal(0,.01,(64,64)),0,1).astype(np.float32)

def glyph_data(pos,neg):
 rank=[[] for _ in range(15)];suit=[[] for _ in range(5)];fonts=list(R.glob('*.ttf'))+list(Path('/usr/share/fonts/truetype/dejavu').glob('*.ttf'))
 realrank=[[] for _ in rank];realsuit=[[] for _ in suit]
 for im,r,s,_ in pos:
  a,b=legacy.card_glyphs(im);realrank[13 if r=='BACK' else RANKS.index(r)].append(a)
  if s<4:realsuit[s]+=[b,legacy.normalise_glyph(im[:44,47:95],'suit')]
  # Off-orientation suit/corner ink must not become a rank.
  for k in [1,2,3]:
   a,b=legacy.card_glyphs(cv2.resize(np.rot90(im,k).copy(),(96,128)));rank[14].append(a)
 for p in fonts:
  for i,r in enumerate(RANKS):
   im=Image.new('L',(110,110),255);ImageDraw.Draw(im).text((55,55),r,font=ImageFont.truetype(str(p),70),fill=0,anchor='mm');rank[i].append(legacy.normalise_glyph(np.array(im)))
 for i in range(4):suit[i]=[draw_suit(i,True),draw_suit(i,False)]
 for im in neg:
  a,b=legacy.card_glyphs(im);rank[14]+=[a,b];suit[4]+=[a,b]
 for i in range(150):
  im=np.zeros((48,48),np.uint8)
  if i%5==1:cv2.line(im,(0,random.randrange(48)),(47,random.randrange(48)),255,random.randint(1,8))
  if i%5==2:cv2.rectangle(im,(random.randrange(15),random.randrange(15)),(random.randrange(30,48),random.randrange(30,48)),255,-1)
  if i%5==3:im=cv2.resize(np.random.randint(0,256,(10,10),np.uint8),(48,48))
  if i%5==4:cv2.circle(im,(24,24),random.randrange(8,22),255,random.randint(1,4))
  rank[14].append(im);suit[4].append(im)
 for bases in suit[:4]:rank[14]+=bases
 for bases in rank[:13]:suit[4]+=bases[:5]
 rank[13]=realrank[13] or [np.zeros((48,48),np.uint8)]
 xs=[];ys=[]
 for i in range(15):
  for _ in range(420 if i<13 else 550):
   pool=realrank[i] if realrank[i] and random.random()<.65 else rank[i]
   xs.append(aug_mask(random.choice(pool)));ys.append([i,4])
 for i in range(5):
  for _ in range(420 if i<4 else 550):
   pool=realsuit[i] if realsuit[i] and random.random()<.65 else suit[i]
   xs.append(aug_mask(random.choice(pool)));ys.append([14,i])
 return torch.from_numpy(np.stack(xs))[:,None],torch.tensor(ys),{'realRankMasks':[len(g) for g in realrank],'realSuitMasks':[len(g) for g in realsuit],'fonts':[p.name for p in fonts]}

def synthetic_card(pos):
 im,r,s,_=random.choice([p for p in pos if p[1]!='BACK'])
 if random.random()<.35:return im.copy(),1 if r=='BACK' else 0
 fonts=list(R.glob('*.ttf'));font=ImageFont.truetype(str(random.choice(fonts)),31)
 rank=random.choice(RANKS);s=random.randrange(4);color=(30,30,190) if s in [1,2] else (25,25,25)
 out=Image.new('RGB',(96,128),(242,242,236));d=ImageDraw.Draw(out);d.text((3,-2),rank,font=font,fill=color[::-1])
 shape=draw_suit(s,True)
 for box in [(51,6,30,30),(28,55,62,62)]:
  x,y,w,h=box;mask=Image.fromarray(shape).resize((w,h));layer=Image.new('RGB',(w,h),color[::-1]);out.paste(layer,(x,y),mask)
 return cv2.cvtColor(np.array(out),cv2.COLOR_RGB2BGR),0

def aug_rgb(im,rotation=True):
 if rotation:im=cv2.resize(np.rot90(im,random.randrange(4)).copy(),(96,128))
 else:im=cv2.resize(im,(96,128))
 points=np.float32([[0,0],[95,0],[95,127],[0,127]])
 target=points+np.random.uniform(-3.5,3.5,(4,2)).astype(np.float32)
 im=cv2.warpPerspective(im,cv2.getPerspectiveTransform(points,target),(96,128),borderMode=cv2.BORDER_REPLICATE)
 hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV).astype(np.float32);hsv[:,:,0]=(hsv[:,:,0]+random.uniform(-5,5))%180;hsv[:,:,1]*=random.uniform(.6,1.5);hsv[:,:,2]*=random.uniform(.62,1.15)
 im=cv2.cvtColor(np.clip(hsv,0,255).astype(np.uint8),cv2.COLOR_HSV2BGR)
 if random.random()<.4:
  w=random.randint(30,80);im=cv2.resize(cv2.resize(im,(w,round(w*4/3))),(96,128))
 if random.random()<.2:im=cv2.GaussianBlur(im,(3,3),random.uniform(.3,1))
 return cv2.resize(im,(64,96)).transpose(2,0,1).astype(np.float32)/255

def verifier_data(pos,neg):
 backs=[im for im,r,_,_ in pos if r=='BACK'];faces=[im for im,r,_,_ in pos if r!='BACK'];xs=[];ys=[]
 for i in range(5200):
  c=i%3
  if c==0:
   im=(random.choice(faces) if random.random()<.70 else synthetic_card(pos)[0])
  elif c==1:
   im=random.choice(backs)
  else:
   im=random.choice(neg)
   if random.random()<.20:
    # Cut fragments and blank paper must not count as complete cards.
    im=random.choice(faces).copy();a=random.randint(0,80);im=im[a:a+45,random.randint(20,50):]
   if random.random()<.12:im=np.full((128,96,3),random.randint(180,255),np.uint8)
  xs.append(aug_rgb(im));ys.append(c)
 return torch.from_numpy(np.stack(xs)),torch.tensor(ys)

def train(model,x,y,name,epochs):
 print(name,'examples',len(y),'params',sum(p.numel() for p in model.parameters()),flush=True)
 opt=torch.optim.AdamW(model.parameters(),lr=.0012,weight_decay=.008);sched=torch.optim.lr_scheduler.CosineAnnealingLR(opt,epochs,eta_min=.00008)
 started=time.perf_counter()
 for epoch in range(epochs):
  model.train();losses=0;correct=0
  for ids in torch.randperm(len(y)).split(128):
   out=model(x[ids]);target=y[ids]
   if name=='glyph':
    loss=nn.functional.cross_entropy(out[:,:15],target[:,0],label_smoothing=.015)+nn.functional.cross_entropy(out[:,15:],target[:,1],label_smoothing=.015)
    correct+=int(((out[:,:15].argmax(1)==target[:,0])&(out[:,15:].argmax(1)==target[:,1])).sum())
   else:
    loss=nn.functional.cross_entropy(out,target,label_smoothing=.01);correct+=int((out.argmax(1)==target).sum())
   opt.zero_grad();loss.backward();nn.utils.clip_grad_norm_(model.parameters(),5);opt.step();losses+=float(loss.detach())*len(ids)
  sched.step();print(name,epoch+1,round(losses/len(y),4),round(correct/len(y),4),'elapsed',round(time.perf_counter()-started,1),flush=True)
 model.eval();path=ROOT/'models'/(name+'.onnx')
 torch.onnx.export(model,x[:1],str(path),input_names=['image'],output_names=['logits'],opset_version=17,dynamic_axes={'image':{0:'batch'},'logits':{0:'batch'}})
 torch.save(model.state_dict(),D/(name+'-v3.pt'))
 return {'parameters':sum(p.numel() for p in model.parameters()),'examples':len(y),'epochs':epochs,'seconds':round(time.perf_counter()-started,1),'shape':list(x.shape[1:])}

if __name__=='__main__':
 recs=records();pos,neg=base_cards(recs);(ROOT/'training/v3-labels.json').write_text(json.dumps(recs,ensure_ascii=False,indent=2))
 print('reviewed positives',len(pos),'negatives',len(neg),flush=True)
 meta={'version':'0.3.0','seed':SEED,'realCrops':len(pos),'reviewedBackgroundCrops':len(neg),'heads':{},'scoresCalibrated':False,'excluded':['bili-cards/025.jpg','bili-cards/026.jpg','poker-a/0057.jpg','v3-frames/bili-630.jpg','v3-frames/long-2075.jpg','v3-frames/long-2082.jpg','v2-unseen/*'],'warning':'Development data, with repeated views of the same physical hands. Not an independent overall accuracy estimate.'}
 x,y=verifier_data(pos,neg);meta['heads']['card']=train(CardNetV3(),x,y,'card',16);del x,y
 x,y,details=glyph_data(pos,neg);meta.update(details);meta['heads']['glyph']=train(GlyphNetV3(),x,y,'glyph',20)
 for name in ['card.onnx','glyph.onnx']:
  p=ROOT/'models'/name;meta.setdefault('files',{})[name]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
 (ROOT/'models/model-card.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2))
 print('TRAINING COMPLETE',flush=True)

"""V2: balanced unique real glyphs, stronger morphology augmentation, larger CNN.
No validation-video pixels or neighbouring held-out hand enter training.
"""
import sys,random,json,hashlib,time
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw,ImageFont
import torch
from torch import nn
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tools'))
from recognizer import normalise_glyph,card_glyphs,find_cards,RANKS
from training_primitives import draw_suit
random.seed(2201);np.random.seed(2201);torch.manual_seed(2201);torch.set_num_threads(2)

class GlyphNetV2(nn.Module):
 def __init__(self,n):
  super().__init__();self.net=nn.Sequential(nn.Conv2d(1,16,3,padding=1),nn.ReLU(),nn.MaxPool2d(2),nn.Conv2d(16,24,3,padding=1),nn.ReLU(),nn.MaxPool2d(2),nn.Conv2d(24,32,3,padding=1),nn.ReLU(),nn.MaxPool2d(2),nn.Flatten(),nn.Linear(32*6*6,64),nn.ReLU(),nn.Dropout(.12),nn.Linear(64,n))
 def forward(self,x):return self.net(x)

def augment(mask):
 m=cv2.getRotationMatrix2D((24,24),random.uniform(-24,24),random.uniform(.67,1.14));m[0,1]+=random.uniform(-.26,.26);m[:,2]+=np.random.uniform(-3,3,2)
 out=cv2.warpAffine(mask,m,(48,48))
 if random.random()<.35:
  kernel=np.ones((2,2),np.uint8);out=(cv2.erode if random.random()<.5 else cv2.dilate)(out,kernel)
 if random.random()<.40:
  side=random.randint(14,38);out=cv2.resize(cv2.resize(out,(side,side)),(48,48))
 if random.random()<.3:out=cv2.GaussianBlur(out,(3,3),random.uniform(.25,.85))
 return np.clip(out.astype(np.float32)/255*random.uniform(.7,1)+np.random.normal(0,.013,(48,48)),0,1).astype(np.float32)

def data():
 synrank=[[] for _ in range(15)];synsuit=[[] for _ in range(5)];realrank=[[] for _ in range(15)];realsuit=[[] for _ in range(5)];records=[]
 fonts=list((ROOT/'research').glob('*.ttf'))+list(Path('/usr/share/fonts/truetype/dejavu').glob('*.ttf'))
 for path in fonts:
  for i,r in enumerate(RANKS):
   im=Image.new('L',(100,100),255);d=ImageDraw.Draw(im);d.text((50,50),r,font=ImageFont.truetype(str(path),65),fill=0,anchor='mm');synrank[i].append(normalise_glyph(np.array(im)))
 for i in range(4):synsuit[i]=[draw_suit(i,True),draw_suit(i,False)]
 for i in range(120):
  im=np.zeros((48,48),np.uint8)
  if i%5==1:cv2.line(im,(0,random.randrange(48)),(47,random.randrange(48)),255,random.randrange(1,8))
  elif i%5==2:cv2.rectangle(im,(random.randrange(15),random.randrange(15)),(random.randrange(30,48),random.randrange(30,48)),255,-1)
  elif i%5==3:im=cv2.resize(np.random.randint(0,256,(10,10),np.uint8),(48,48))
  elif i%5==4:cv2.circle(im,(24,24),random.randrange(8,22),255,random.randrange(1,4))
  synrank[14].append(im);synsuit[4].append(im)
 back=np.zeros((48,48),np.uint8);cv2.rectangle(back,(5,3),(42,44),255,2);cv2.rectangle(back,(10,8),(37,39),140,1);synrank[13]=[back,255-back]
 def add(card,rank,suit,source):
  a,b=card_glyphs(card);ri=13 if rank=='BACK' else RANKS.index(rank);realrank[ri].append(a)
  if suit<4:
   realsuit[suit].append(b);realsuit[suit].append(normalise_glyph(card[:44,47:95],'suit'))
  records.append({'source':source,'rank':rank,'suit':suit})
 baseline={'trainingCrops':json.loads((ROOT/'training/v01-training-records.json').read_text('utf-8'))}
 for key,(r,s) in baseline['trainingCrops'].items():
  p=ROOT/'research'/(key+'.png') if key.startswith('fullcard-') else ROOT/'research/cards'/(key+'.png')
  card=cv2.imread(str(p));
  if card is not None:add(card,r,s,key)
 groups=[('full-1435.jpg',[.42,.45,.75,.63],[(0,0,'Q',1),(1,0,'9',2)]),('full-2066.jpg',[.25,.37,.85,.55],[(1,0,'8',2),(2,0,'6',3),(3,0,'8',0),(4,0,'7',1)]),('bili-cards/017.jpg',[.1,.3,.39,.94],[(1,1,'K',2),(2,1,'2',1)]),('bili-cards/022.jpg',[.62,.26,.86,.65],[(1,0,'7',3),(2,0,'9',0),(3,0,'J',2)])]
 for file,region,labels in groups:
  cards=find_cards(cv2.imread(str(ROOT/'research'/file)),region)
  for i,k,r,s in labels:
   card=cv2.resize(np.rot90(cards[i]['image'],k).copy(),(96,128));add(card,r,s,file+':'+str(i)+':rotation'+str(k))
 for g in synsuit[:4]:synrank[14].extend(g)
 for g in synrank[:13]:synsuit[4].extend(g[:4])
 # Dedupe, rather than multiplying the last real sample's weight exponentially.
 def unique(g):return [np.frombuffer(v,dtype=np.uint8).reshape(48,48).copy() for v in dict.fromkeys(x.tobytes() for x in g)]
 return [(list(map(unique,synrank)),list(map(unique,realrank)),15,1200,'rank'),(list(map(unique,synsuit)),list(map(unique,realsuit)),5,1200,'suit')],records,[p.name for p in fonts]

def train(syn,real,n,count,name):
 xs=[];ys=[]
 for i in range(n):
  for _ in range(count):
   choices=real[i] if real[i] and random.random()<.55 else syn[i]
   xs.append(augment(random.choice(choices)));ys.append(i)
 x=torch.from_numpy(np.stack(xs))[:,None];y=torch.tensor(ys);model=GlyphNetV2(n);opt=torch.optim.AdamW(model.parameters(),lr=.0015,weight_decay=.005)
 for epoch in range(22):
  model.train();losses=0;correct=0
  if epoch==15:
   for group in opt.param_groups:group['lr']=.0004
  for ids in torch.randperm(len(y)).split(256):
   out=model(x[ids]);loss=nn.functional.cross_entropy(out,y[ids],label_smoothing=.03);opt.zero_grad();loss.backward();opt.step();losses+=float(loss.detach())*len(ids);correct+=int((out.argmax(1)==y[ids]).sum())
  print(name,epoch+1,round(losses/len(y),4),round(correct/len(y),4),flush=True)
 model.eval();torch.onnx.export(model,torch.zeros(1,1,48,48),str(ROOT/'models'/(name+'.onnx')),input_names=['image'],output_names=['logits'],opset_version=17,dynamic_axes={'image':{0:'batch'},'logits':{0:'batch'}})
 return {'parameters':sum(p.numel() for p in model.parameters()),'syntheticBases':[len(g) for g in syn],'realUniqueGlyphs':[len(g) for g in real]}

if __name__=='__main__':
 sets,records,fonts=data();results={}
 for syn,real,n,count,name in sets:results[name]=train(syn,real,n,count,name)
 meta={'version':'0.2.0','seed':2201,'architecture':'GlyphNetV2 16/24/32, dense64, dropout, balanced real/synthetic sampling','trainingRecords':records,'trainingPhysicalCardCrops':len(records),'fonts':fonts,'heads':results,'epochs':22,'examplesPerClass':1200,'runtime':'OpenCV DNN CPU; no ONNX Runtime dependency','warning':'Small development dataset. Old regression cases influenced development; no overall accuracy claim. BV1eD5x6NEEs and Bili frames025/026 were excluded from training.'}
 for p in (ROOT/'models').glob('*.onnx'):meta.setdefault('files',{})[p.name]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
 (ROOT/'models/model-card.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),'utf-8')

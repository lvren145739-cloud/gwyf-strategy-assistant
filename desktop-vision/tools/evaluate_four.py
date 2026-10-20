"""Synthetic open-4 layouts and a reviewed video crop, never user photo pixels."""
from pathlib import Path
import sys,importlib.util,json,cv2,numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tools'))
from recognizer import Recognizer,normalise_glyph,RANKS,SUITS
from training_primitives import draw_suit
import train_v3 as t
D=ROOT/'research/v031-data';D.mkdir(exist_ok=True)
new=Recognizer();spec=importlib.util.spec_from_file_location('v030',ROOT.parent/'vision-v3/recognizer.py');oldmod=importlib.util.module_from_spec(spec);spec.loader.exec_module(oldmod);old=oldmod.Recognizer(ROOT.parent/'vision-v3/models')
pos,_=t.base_cards(t.records())
source=cv2.resize(cv2.imread(str(D/'reviewed-four-hearts.png')),(144,192));four=normalise_glyph(source[:76,:65],clean_border=True)
def card(rank,suit):
 out=np.full((192,144,3),241,np.uint8)
 if rank=='BACK':
  cv2.rectangle(out,(14,14),(130,178),(220,205,160),-1);cv2.rectangle(out,(25,25),(119,167),(235,217,177),5);return out
 color=np.array((15,15,215) if suit in ['hearts','diamonds'] else (24,24,24))
 a=four if rank=='4' else t.legacy.card_glyphs(next(p[0] for p in pos if p[1]==rank))[0]
 def ink(mask,x,y,w,h):
  alpha=cv2.resize(mask,(w,h)).astype(np.float32)[:,:,None]/255
  out[y:y+h,x:x+w]=np.clip(out[y:y+h,x:x+w]*(1-alpha)+color*alpha,0,255).astype(np.uint8)
 ink(a,3,4,55,65);s=draw_suit(SUITS.index(suit),True);ink(s,78,3,60,60);ink(s,43,81,97,108)
 return out
layouts=[]
for dealer_suit,player in [('spades',[('2','clubs'),('3','hearts')]),('hearts',[('7','spades'),('10','diamonds')]),('clubs',[('9','clubs'),('8','clubs')])]:
 for angle in [0,-20,20]:
  canvas=np.full((1000,1600,3),(83,103,78),np.uint8)
  positions=[np.float32([[520,640],[700,640],[740,900],[480,900]]),np.float32([[910,640],[1090,640],[1130,900],[870,900]]),np.float32([[700,320],[850,320],[870,450],[680,450]]),np.float32([[1010,320],[1160,320],[1180,450],[990,450]])]
  cards=[card(*p) for p in player]+[card('4',dealer_suit),card('BACK',None)]
  for c,q in zip(cards,positions):
   matrix=cv2.getPerspectiveTransform(np.float32([[0,0],[143,0],[143,191],[0,191]]),q)
   mask=cv2.warpPerspective(np.full((192,144),255,np.uint8),matrix,(1600,1000));warped=cv2.warpPerspective(c,matrix,(1600,1000));canvas[mask>0]=warped[mask>0]
  cv2.putText(canvas,str(sum(10 if p[0]=='10' else int(p[0]) for p in player)),(750,635),cv2.FONT_HERSHEY_SIMPLEX,2.5,(255,255,255),8,cv2.LINE_AA)
  matrix=cv2.getRotationMatrix2D((800,550),angle,.9);canvas=cv2.warpAffine(canvas,matrix,(1600,1000),borderValue=(83,103,78))
  name=f'four-{dealer_suit}-{angle}';cv2.imwrite(str(D/(name+'.png')),canvas)
  expected=sorted([['dealer','4',dealer_suit]]+[['player',r,s] for r,s in player])
  record={'name':name,'expected':expected,'scope':'Synthetic scene from a reviewed gameplay glyph; not original attachment pixels.'}
  for version,model in [('v030',old),('v031',new)]:
   out=model.read(canvas,{},'blackjack');pred=sorted([[c['role'],c['rank'],c['suit']] for c in out['cards'] if not c['faceDown']],key=str)
   record[version]={'exact':pred==expected,'predicted':pred,'autoReady':out['autoReady'],'cards':[{k:v for k,v in c.items() if k not in ['preview','quad']} for c in out['cards']]}
  layouts.append(record);print(name,record['v030']['exact'],record['v031']['exact'],record['v031']['autoReady'],record['v031']['predicted'],flush=True)
report={'scope':'Selected synthetic open-4 layouts, not user attachment or independent accuracy tests. Original real 4 source was used for refinement.','cases':layouts,'summary':{'cases':len(layouts),'v030Exact':sum(c['v030']['exact'] for c in layouts),'v031Exact':sum(c['v031']['exact'] for c in layouts),'automatic':sum(c['v031']['autoReady'] for c in layouts)}}
(ROOT/'tests/four-evaluation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(report['summary'],flush=True)

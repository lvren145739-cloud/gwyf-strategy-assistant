"""Synthetic regressions of the reported layout, NOT the user's original photos.
Uses already reviewed game card crops. Not an independent accuracy benchmark.
"""
from pathlib import Path
import json,cv2,numpy as np
r=Path(__file__).resolve().parents[1];research=r/'research';d=research/'v3-data';out=d/'reconstructed';out.mkdir(exist_ok=True)
rows=json.loads((d/'reviewed-initial.json').read_text());cards={}
for rank,suit,key in [('9',3,'9c'),('8',3,'8c'),('A',1,'ah'),('BACK',4,'back')]:
 c=next(c for c in rows if c.get('rank')==rank and c.get('suit')==suit and c.get('rotation',0)==0)
 cards[key]=cv2.imread(str(research/c['file']))
def make(name,angle,offset,overlay):
 image=np.full((1000,1600,3),(139,164,167),np.uint8)
 # Black serif-like table text, large floating totals and white UI decoys.
 cv2.rectangle(image,(550,470),(1520,555),(55,65,65),5);cv2.putText(image,'Beat the dealer without busting 21',(580,525),cv2.FONT_HERSHEY_SIMPLEX,1.5,(45,55,55),3)
 cv2.rectangle(image,(20,120),(230,240),(236,236,236),-1);cv2.putText(image,'17',(35,195),cv2.FONT_HERSHEY_SIMPLEX,2.5,(30,30,30),5)
 cv2.circle(image,(1420,180),115,(238,238,235),-1);cv2.ellipse(image,(1385,165),(20,45),0,0,360,(45,25,40),-1);cv2.ellipse(image,(1470,165),(20,45),0,0,360,(45,25,40),-1)
 positions={'9c':np.float32([[750,655],[930,650],[965,890],[720,900]]),'8c':np.float32([[1070,650],[1250,655],[1290,900],[1040,890]]),'ah':np.float32([[950,330],[1085,330],[1100,450],[935,450]]),'back':np.float32([[1185,330],[1320,330],[1340,450],[1165,450]])}
 for key,quad in positions.items():
  h,w=cards[key].shape[:2];m=cv2.getPerspectiveTransform(np.float32([[0,0],[w-1,0],[w-1,h-1],[0,h-1]]),quad)
  mask=cv2.warpPerspective(np.full((h,w),255,np.uint8),m,(1600,1000));warped=cv2.warpPerspective(cards[key],m,(1600,1000));image[mask>0]=warped[mask>0]
 if overlay:cv2.putText(image,'17',(850,680),cv2.FONT_HERSHEY_SIMPLEX,2.5,(255,255,255),8,cv2.LINE_AA)
 m=cv2.getRotationMatrix2D((1020,590),angle,.88);m[:,2]+=np.array(offset);image=cv2.warpAffine(image,m,(1600,1000),borderValue=(120,150,155))
 path=out/(name+'.png');cv2.imwrite(str(path),image);return {'name':name,'file':str(path.relative_to(research)),'expected':[['player','9','clubs'],['player','8','clubs'],['dealer','A','hearts']],'scope':'Synthetic reconstruction of the user-reported failure layout; not original attachment pixels.'}
records=[make('front-with-total',0,(-80,-30),True),make('slanted-left',-24,(-90,-40),True),make('slanted-right',24,(-90,-40),False)]
(r/'tests/reconstructed-cases.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),'utf-8');print(len(records),'synthetic cases')

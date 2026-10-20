"""Local whole-card validation, high-resolution glyphs and visible-table grouping.
No game memory, network requests or hidden-card inference.
"""
from pathlib import Path
import base64,time
import cv2,numpy as np
cv2.setNumThreads(1)
ROOT=Path(__file__).resolve().parent
RANKS=['A','2','3','4','5','6','7','8','9','10','J','Q','K']
SUITS=['spades','hearts','diamonds','clubs']

def png_data(im):
 ok,data=cv2.imencode('.png',im)
 if not ok:raise ValueError('图片编码失败')
 return 'data:image/png;base64,'+base64.b64encode(data).decode('ascii')

def order_corners(points):
 p=np.asarray(points,np.float32).reshape(4,2);center=p.mean(axis=0)
 p=p[np.argsort(np.arctan2(p[:,1]-center[1],p[:,0]-center[0]))]
 return np.roll(p,-int(np.argmin(p.sum(axis=1))),axis=0).astype(np.float32)

def quad_iou(a,b):
 area_a=abs(cv2.contourArea(np.asarray(a,np.float32)));area_b=abs(cv2.contourArea(np.asarray(b,np.float32)))
 try:intersection,_=cv2.intersectConvexConvex(np.asarray(a,np.float32),np.asarray(b,np.float32))
 except cv2.error:return 0.
 return float(intersection/max(1,area_a+area_b-intersection))

def valid_region(region):
 if not isinstance(region,(list,tuple)) or len(region)!=4 or not all(isinstance(x,(int,float)) and np.isfinite(x) for x in region):raise ValueError('牌区无效')
 l,t,r,b=region
 if not 0<=l<r<=1 or not 0<=t<b<=1:raise ValueError('请框出有效牌区')
 return region

def center_inside(item,region,w,h):
 l,t,r,b=valid_region(region);x,y,cw,ch=item['rect'];cx,cy=(x+cw/2)/w,(y+ch/2)/h
 return l<=cx<=r and t<=cy<=b

def find_cards(image,region=None):
 """Find full quads first. A user region filters centers, never cuts a card.
 Multi-scale opening separates thin floating totals from the paper underneath.
 """
 if image is None or image.ndim!=3 or min(image.shape[:2])<20:raise ValueError('截图无效')
 h,w=image.shape[:2];scale=min(1,1920/max(h,w));small=cv2.resize(image,(round(w*scale),round(h*scale))) if scale<1 else image
 sh,sw=small.shape[:2];hsv=cv2.cvtColor(small,cv2.COLOR_BGR2HSV);found=[]
 sizes=sorted({1,max(3,round(sh*.007))|1,max(5,round(sh*.016))|1})
 for brightness in [190,160]:
  base=cv2.inRange(hsv,np.array([0,0,brightness]),np.array([180,110,255]))
  outer,_=cv2.findContours(base,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
  filled=np.zeros_like(base);cv2.drawContours(filled,outer,-1,255,cv2.FILLED)
  for kernel in sizes:
   # Fill printed glyph holes before opening: otherwise the ink cuts the paper
   # into fragments and deletes its corner. Only thin external totals are removed.
   mask=base if kernel==1 else cv2.morphologyEx(filled,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(kernel,kernel)))
   contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
   for contour in contours:
    area=cv2.contourArea(contour);x,y,cw,ch=cv2.boundingRect(contour)
    if area<max(65,sw*sh*.000065) or area>sw*sh*.32 or cw<12 or ch<10 or not .22<cw/ch<7 or area/(cw*ch)<.34:continue
    hull=cv2.convexHull(contour)
    if area/max(1,cv2.contourArea(hull))<.72:continue
    q=None
    for epsilon in [.015,.025,.035,.045,.06,.08]:
     candidate=cv2.approxPolyDP(hull,epsilon*cv2.arcLength(hull,True),True)
     if len(candidate)==4 and cv2.isContourConvex(candidate):q=order_corners(candidate);break
    if q is None:continue
    if kernel>1:
     center=q.mean(axis=0);q=center+(q-center)*(1+.30*kernel/max(12,min(cw,ch)))
    q=q/scale
    if any(quad_iou(q,c['quad'])>.94 for c in found):continue
    ox,oy,ow,oh=cv2.boundingRect(q)
    item={'rect':[int(ox),int(oy),int(ow),int(oh)],'quad':q.tolist(),
          'clipped':ox<=1 or oy<=1 or ox+ow>=w-1 or oy+oh>=h-1,
          'geometry':round(area/max(1,cv2.contourArea(hull)),4)}
    if region is not None and not center_inside(item,region,w,h):continue
    mat=cv2.getPerspectiveTransform(q,np.float32([[0,0],[143,0],[143,191],[0,191]]))
    item['image']=cv2.warpPerspective(image,mat,(144,192))
    found.append(item)
 # Limit pathological UI pages without selecting a random subset of tiny boxes.
 return sorted(sorted(found,key=lambda c:c['rect'][2]*c['rect'][3],reverse=True)[:240],key=lambda c:c['rect'][0])

def normalise_glyph(image,kind='rank',clean_border=False):
 gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY) if image.ndim==3 else image
 _,ink=cv2.threshold(gray,0,255,cv2.THRESH_BINARY_INV|cv2.THRESH_OTSU)
 if clean_border:
  h,w=gray.shape;dy,dx=max(1,h//6),max(1,w//6)
  # Estimate ink against the paper interior, not the dark table beyond its
  # rounded corner. Otherwise a faint red lower stroke of 4 disappears.
  threshold,_=cv2.threshold(gray[dy:h-dy,dx:w-dx],0,255,cv2.THRESH_BINARY_INV|cv2.THRESH_OTSU)
  ink=np.where(gray<=threshold,255,0).astype(np.uint8)
 n,labels,stats,_=cv2.connectedComponentsWithStats(ink)
 components=[(i,s) for i,s in enumerate(stats[1:],1) if s[4]>=3]
 if clean_border:
  # A rounded paper corner can leave a strip of dark table in the crop. It is
  # not printed ink: discard boundary strips, keeping disconnected digits (10).
  h,w=ink.shape
  components=[(i,s) for i,s in components if not
              ((s[0]==0 or s[1]==0 or s[0]+s[2]>=w or s[1]+s[3]>=h) and
               (s[2]>.65*w and s[3]<.28*h or s[3]>.65*h and s[2]<.28*w))]
 if not components:return np.zeros((48,48),np.uint8)
 biggest=max(s[4] for _,s in components);clean=np.zeros_like(ink)
 for i,s in components:
  if s[4]>=biggest*.10:clean[labels==i]=255
 ys,xs=np.where(clean>0)
 if not len(xs):return np.zeros((48,48),np.uint8)
 glyph=clean[ys.min():ys.max()+1,xs.min():xs.max()+1];gh,gw=glyph.shape;scale=min(38/gw,38/gh)
 gw,gh=max(1,round(gw*scale)),max(1,round(gh*scale));glyph=cv2.resize(glyph,(gw,gh),interpolation=cv2.INTER_AREA);out=np.zeros((48,48),np.uint8)
 out[(48-gh)//2:(48-gh)//2+gh,(48-gw)//2:(48-gw)//2+gw]=glyph
 return out

def card_glyphs(card):
 # Preserve the training geometry, with additional original-frame pixels.
 h,w=card.shape[:2]
 return normalise_glyph(card[:round(h*51/128),:round(w*43/96)]),normalise_glyph(card[round(h*49/128):round(h*126/128),round(w*27/96):round(w*95/96)],'suit')

def ink_color(crop):
 gray=cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY)
 _,mask=cv2.threshold(gray,0,255,cv2.THRESH_BINARY_INV|cv2.THRESH_OTSU)
 pixels=crop[(mask>0)&(gray<180)]
 if len(pixels)<8:return None
 advantage=pixels[:,2].astype(float)-np.maximum(pixels[:,0],pixels[:,1])
 red=float(np.median(advantage))
 return 'red' if red>40 else 'black' if red<20 else None

def consensus(vectors,valid=None,weights=None):
 """Model support, never a calibrated probability of correctness.
 Two distinct networks and two crops can recover a damaged individual crop.
 """
 vectors=np.asarray(vectors);weights=np.asarray(weights or [1.25,1.25,1.,1.])
 support=np.average(vectors,axis=0,weights=weights)
 if valid is not None:
  allowed=np.zeros_like(support);allowed[valid]=1;allowed[-1]=1;support*=allowed
 winner=int(support.argmax());votes=sorted([float(v[winner]) for v in vectors],reverse=True)
 score=float(np.mean(votes[:2]));strong=sum(v>.85 for v in votes)
 return winner,score,support,strong

def softmax(logits):
 x=logits-logits.max(axis=1,keepdims=True);p=np.exp(x);return p/p.sum(axis=1,keepdims=True)

class DNNSession:
 def __init__(self,path):
  self.net=cv2.dnn.readNetFromONNX(np.frombuffer(Path(path).read_bytes(),np.uint8));self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
  if int(cv2.__version__.split('.')[0])<5:self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
 def run(self,_,inputs):
  self.net.setInput(np.ascontiguousarray(inputs['image'],np.float32));return [self.net.forward()]
 def predict(self,x):
  parts=[]
  for i in range(0,len(x),48):parts.append(self.run(None,{'image':x[i:i+48]})[0])
  return np.concatenate(parts) if parts else np.empty((0,0),np.float32)

class HeadSession:
 def __init__(self,shared,start,end):self.shared=shared;self.start=start;self.end=end
 def run(self,_,inputs):
  x=inputs['image']
  if x.shape[-2:]!=(64,64):x=np.stack([cv2.resize(a[0],(64,64)) for a in x])[:,None]
  return [self.shared.run(None,{'image':x})[0][:,self.start:self.end]]

class Recognizer:
 def __init__(self,model_dir=None):
  folder=Path(model_dir) if model_dir else ROOT/'models'
  self.glyph=DNNSession(folder/'glyph.onnx');self.card=DNNSession(folder/'card.onnx')
  self.legacy_rank=DNNSession(folder/'rank-v2.onnx');self.legacy_suit=DNNSession(folder/'suit-v2.onnx')
  self.recovery_glyph=DNNSession(folder/'glyph-open.onnx');self.recovery_rank=DNNSession(folder/'rank-open.onnx')
  self.rank=HeadSession(self.glyph,0,15);self.suit=HeadSession(self.glyph,15,20);self.backend='OpenCV DNN / CPU · V3.1'

 @staticmethod
 def classify(session,batch):
  if not batch:return []
  x=np.stack([cv2.resize(a,(64,64)) for a in batch]).astype(np.float32)[:,None]/255
  p=softmax(session.run(None,{'image':x})[0]);return [(int(a.argmax()),float(a.max()),a.tolist()) for a in p]

 def read(self,image,regions=None,mode='blackjack'):
  start=time.perf_counter();h,w=image.shape[:2];regions=regions or {};manual=bool(regions)
  if mode not in ('blackjack','poker'):raise ValueError('识别模式无效')
  for role,region in regions.items():
   if role not in ('player','dealer'):raise ValueError('牌区归属无效')
   if region is not None:valid_region(region)
  items=find_cards(image)
  if manual:items=[c for c in items if any(r and center_inside(c,r,w,h) for role,r in regions.items() if mode=='blackjack' or role=='player')]
  if not items:return {'cards':[],'hiddenCount':0,'rejectedCount':0,'warnings':['没有找到完整牌面。'],'autoReady':False,'recognitionMs':round((time.perf_counter()-start)*1000,1)}
  inputs=np.stack([cv2.resize(c['image'],(64,96)).transpose(2,0,1) for c in items]).astype(np.float32)/255
  verify=softmax(self.card.predict(inputs));eligible=[];rejected=0
  for c,p in zip(items,verify):
   c['cardScore']=float(p[0]);c['backScore']=float(p[1]);c['backgroundScore']=float(p[2])
   if p[2]>.90 or (p[0]<.25 and p[1]<.80):rejected+=1;continue
   eligible.append(c)
  # Analyze only likely cards. Ordinary UI rectangles never reach the glyph model.
  items=eligible
  glyphs=[];variants=[]
  for item in items:
   for k in range(4):
    card=cv2.resize(np.rot90(item['image'],k).copy(),(144,192));variants.append(card)
    a,b=card_glyphs(card);top=normalise_glyph(card[:66,70:143],'suit');alt=normalise_glyph(card[:82,:69])
    clean=normalise_glyph(card[:76,:65],clean_border=True);clean_alt=normalise_glyph(card[:82,:69],clean_border=True)
    glyphs.extend([a,alt,clean,clean_alt,b,top])
  if glyphs:
   x=np.stack([cv2.resize(a,(64,64)) for a in glyphs]).astype(np.float32)[:,None]/255
   logits=self.glyph.predict(x);rp=softmax(logits[:,:15]);sp=softmax(logits[:,15:])
   oldx=np.stack(glyphs).astype(np.float32)[:,None]/255
   oldrp=softmax(self.legacy_rank.predict(oldx));oldsp=softmax(self.legacy_suit.predict(oldx))
   # Only cleaned rank crops go through the specialist networks. Keeping the
   # original networks as primary preserves already readable/occluded ranks.
   recovery_indices=[j for j in range(len(glyphs)) if j%6 in (2,3)]
   recovered=softmax(self.recovery_glyph.predict(x[recovery_indices])[:,:15])
   recovered_small=softmax(self.recovery_rank.predict(oldx[recovery_indices]))
  results=[]
  for i,item in enumerate(items):
   scores=[];details=[]
   for k in range(4):
    j=(i*4+k)*6
    ri,rankscore,rankp,strong=consensus([rp[j],rp[j+1],oldrp[j],oldrp[j+1]])
    fallback=consensus([rp[j+2],rp[j+3],oldrp[j+2],oldrp[j+3]])
    # Border cleanup is a second reading, not a lower confidence threshold.
    # It may recover a rejected crop; a confidently read original keeps priority.
    rank_margin=float(np.sort(rankp)[-1]-np.sort(rankp)[-2])
    fallback_margin=float(np.sort(fallback[2])[-1]-np.sort(fallback[2])[-2])
    if (ri>=13 or rankscore<.94 or strong<2 or rank_margin<.30) and fallback[0]<13 and fallback[1]>=.94 and fallback[3]>=2 and fallback_margin>=.30:
     ri,rankscore,rankp,strong=fallback
    rank_margin=float(np.sort(rankp)[-1]-np.sort(rankp)[-2])
    if ri>=13 or rankscore<.94 or strong<2 or rank_margin<.30:
     q=(i*4+k)*2
     expert=consensus([recovered[q],recovered[q+1],recovered_small[q],recovered_small[q+1]])
     expert_margin=float(np.sort(expert[2])[-1]-np.sort(expert[2])[-2])
     if expert[0]<13 and expert[1]>=.97 and expert[3]>=3 and expert_margin>.40:
      ri,rankscore,rankp,strong=expert
    card=variants[i*4+k];large_color=ink_color(card[74:189,40:143]);small_color=ink_color(card[:66,70:143]);color=large_color if large_color==small_color or small_color is None else small_color if large_color is None else None
    allowed=[1,2] if color=='red' else [0,3] if color=='black' else None
    si,suit_score,suitp,suit_strong=consensus([sp[j+4],sp[j+5],oldsp[j+4],oldsp[j+5]],allowed)
    # A single crop cannot promote a different suit over two mutually supported
    # positions; ink colour also rules out red/black suit contradictions.
    disagreement=large_color is not None and small_color is not None and large_color!=small_color
    quality=rankscore*suit_score*min(1.,strong/2)*min(1.,suit_strong/2)
    scores.append(quality if ri<13 and si<4 else 0)
    details.append((ri,rankscore,rankp,strong>=2,si,suit_score,disagreement))
   best=int(np.argmax(scores));ri,rankscore,rankp,rcons,si,suit_score,disagree=details[best]
   image0=item['image'];hsv=cv2.cvtColor(image0,cv2.COLOR_BGR2HSV);blue=float(np.mean((hsv[:,:,0]>=65)&(hsv[:,:,0]<=125)&(hsv[:,:,1]>=20)))
   back=item['backScore']>.87 and blue>.20 and item['backScore']>item['cardScore']
   if mode=='poker' and back:rejected+=1;continue
   rank=RANKS[ri] if ri<13 else None;suit=SUITS[si] if si<4 else None;issues=[]
   if not back:
    if item['cardScore']<.80:issues.append('整张牌面判断不够确定')
    if rankscore<.80 or ri>=13:rank=None;issues.append('点数不够清晰')
    if not rcons:issues.append('两次字形读取不一致')
    if suit_score<.80:suit=None;issues.append('花色不够清晰')
    if disagree:issues.append('大小花色不一致')
    if len(scores)>1 and sorted(scores,reverse=True)[0]-sorted(scores,reverse=True)[1]<.10:issues.append('牌面方向不够确定')
   if back:rank=None;suit=None
   if item['clipped']:rank=None;issues.append('牌面超出截图边缘')
   margin=float(np.sort(rankp)[-1]-np.sort(rankp)[-2])
   if not back and margin<.30:issues.append('点数模型意见仍有分歧')
   review=bool(issues or not back and (rankscore<.94 or suit_score<.92 or item['cardScore']<.94 or margin<.30))
   if not back and ri>=13 and rankscore>.97:
    rejected+=1;continue
   if not back and item['cardScore']<.80 and (rank is None or suit is None or rankscore<.94 or suit_score<.92):
    rejected+=1;continue
   result={k:item[k] for k in ('rect','quad','cardScore')}
   result.update(rank=rank,suit=suit,faceDown=bool(back),score=round(rankscore,4),suitScore=round(suit_score,4),rotation=best*90,review=review,issues=issues,preview=png_data(cv2.resize(variants[i*4+best],(96,128))),_selection=float(item['backScore'] if back else item['cardScore']*max(scores)))
   results.append(result)
  # Duplicate proposals from thresholds/opening are the same physical object.
  chosen=[]
  for c in sorted(results,key=lambda c:c['_selection'],reverse=True):
   if not any(quad_iou(c['quad'],a['quad'])>.48 for a in chosen):chosen.append(c)
  chosen.sort(key=lambda c:c['rect'][0]);warnings=[]
  uncertain=[c for c in chosen if not c['faceDown'] and c['rank'] is None and c['suit'] is None]
  chosen=[c for c in chosen if c not in uncertain]
  rejected+=len(uncertain)
  if manual:
   for c in chosen:
    roles=[(role,r) for role,r in regions.items() if r and center_inside(c,r,w,h) and (role=='player' or mode=='blackjack')]
    c['role']=min(roles,key=lambda item:((c['rect'][0]+c['rect'][2]/2)/w-(item[1][0]+item[1][2])/2)**2+((c['rect'][1]+c['rect'][3]/2)/h-(item[1][1]+item[1][3])/2)**2)[0]
  else:
   chosen,group_warnings=self.group_table(chosen,mode,w,h);warnings+=group_warnings
  suspicious=[]
  for u in uncertain:
   ux,uy,uw,uh=u['rect'];uc=np.array([ux+uw/2,uy+uh/2])
   if u['cardScore']>.97 and any(.60<max(uw,uh)/max(c['rect'][2:])<1.7 and np.linalg.norm(uc-np.array([c['rect'][0]+c['rect'][2]/2,c['rect'][1]+c['rect'][3]/2]))<1.5*max(c['rect'][2:]) for c in chosen):suspicious.append({'quad':u['quad'],'rect':u['rect'],'review':True})
  if suspicious:warnings.append(f'另有{len(suspicious)}处可能未读完整的牌面，请核对。')
  for c in chosen:
   c.pop('_selection',None)
   if c['faceDown'] and c['role']!='dealer':c['faceDown']=False;c['rank']=None;c['review']=True;c['issues'].append('自己的暗牌不能读取')
  visible=[c for c in chosen if not c['faceDown']]
  player=[c for c in visible if c['role']=='player'];dealer=[c for c in visible if c['role']=='dealer']
  complete=(len(player)==5 and len({(c['rank'],c['suit']) for c in player})==5) if mode=='poker' else 2<=len(player)<=16 and 1<=len(dealer)<=16
  auto_ready=bool(complete and not warnings and visible and all(c['rank'] and c['suit'] and not c['review'] for c in visible) and all(not c['review'] for c in chosen))
  if mode=='poker' and len(player)!=5:warnings.append(f'扑克需要完整五张，当前检测到{len(player)}张。')
  if mode=='blackjack' and (len(player)<2 or not dealer):warnings.append('没有确定完整的玩家牌和庄家明牌。')
  return {'cards':chosen,'hiddenCount':sum(c['faceDown'] for c in chosen),'rejectedCount':rejected,'warnings':warnings,'uncertainCards':suspicious,'autoReady':auto_ready,'recognitionMs':round((time.perf_counter()-start)*1000,1)}

 @staticmethod
 def group_table(cards,mode,w,h):
  if not cards:return [],[]
  def center(c):x,y,cw,ch=c['rect'];return np.array([x+cw/2,y+ch/2])
  # Connected card rows belong to one nearby table. Never use a distant table
  # merely to fill in missing cards in the selected foreground hand.
  remaining=list(cards);groups=[]
  while remaining:
   group=[remaining.pop(0)];changed=True
   while changed:
    changed=False
    for c in remaining[:]:
     if any(np.linalg.norm(center(c)-center(a))<2.6*min(max(a['rect'][2:]),max(c['rect'][2:]))+.4*max(a['rect'][2:]+c['rect'][2:]) for a in group):group.append(c);remaining.remove(c);changed=True
   groups.append(group)
  chosen=max(groups,key=lambda g:sum(c['rect'][2]*c['rect'][3] for c in g));warnings=[]
  if mode=='poker':
   if len(chosen)>5:
    # Cards that were replaced can remain behind the active five-card row.
    # Fit the row in screen space; do not count a discarded table card as sixth.
    best_row=None;best_score=-1
    for i,a in enumerate(chosen):
     for b in chosen[i+1:]:
      delta=center(b)-center(a);length=float(np.linalg.norm(delta))
      if length<1:continue
      normal=np.array([-delta[1],delta[0]])/length
      row=[c for c in chosen if abs(float(np.dot(center(c)-center(a),normal)))<.32*np.hypot(c['rect'][2],c['rect'][3])]
      if len(row)!=5:continue
      score=sum(c['rect'][2]*c['rect'][3] for c in row)
      if score>best_score:best_score=score;best_row=row
    if best_row is not None:chosen=best_row
   for c in chosen:c['role']='player'
   return chosen,warnings
  backs=[c for c in chosen if c['faceDown']]
  if len(backs)==1:
   back=backs[0];faces=[c for c in chosen if not c['faceDown']]
   if faces:
    nearest=min(faces,key=lambda c:np.linalg.norm(center(c)-center(back)))
    distance=float(np.linalg.norm(center(nearest)-center(back)));size=max(back['rect'][2:]+nearest['rect'][2:])
    if distance<2.6*size:
     for c in chosen:c['role']='dealer' if c is back or c is nearest else 'player'
     if len(faces)>=3:return chosen,warnings
  # Fallback only when upper/lower rows separate clearly. Ambiguous side views
  # stay editable instead of silently exchanging dealer/player roles.
  order=sorted(chosen,key=lambda c:center(c)[1]);ys=[center(c)[1] for c in order]
  gaps=[ys[i+1]-ys[i] if len(order)-i-1>=2 else -1 for i in range(len(order)-1)]
  if gaps and max(gaps)>max(h*.035,np.median([c['rect'][3] for c in chosen])*.30):
   split=int(np.argmax(gaps))+1
   for i,c in enumerate(order):c['role']='dealer' if i<split else 'player'
  else:
   for c in chosen:c['role']='dealer' if c['faceDown'] else 'player';c['review']=True
   warnings.append('牌的归属不够确定，请核对或框选两方牌区。')
  return chosen,warnings

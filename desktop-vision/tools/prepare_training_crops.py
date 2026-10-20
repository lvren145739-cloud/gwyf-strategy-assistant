"""Rebuild manually labelled crop files after research frames were extracted.

See DATA_SOURCES.md. No downloading or training runs implicitly at app launch.
"""
import json,sys
from pathlib import Path
import cv2,numpy as np
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from training.legacy_geometry import find_cards
def order_corners(q):
    p=np.asarray(q,np.float32).reshape(4,2);p=p[np.argsort(p[:,1])];top=p[:2][np.argsort(p[:2,0])];bottom=p[2:][np.argsort(p[2:,0])];return np.float32([top[0],top[1],bottom[1],bottom[0]])
research=root/'research';(research/'cards').mkdir(parents=True,exist_ok=True)
metadata=json.loads((root/'models/model-card.json').read_text('utf-8'))
regions={'bj-a':[.40,.20,.80,.60],'bj-b':[.36,.30,.70,.57],'poker-a':[.30,.38,.92,.57]}

def legacy_crops(im,region):
    h,w=im.shape[:2];l,t,r,b=region;x0,y0,x1,y1=int(l*w),int(t*h),int(r*w),int(b*h);roi=im[y0:y1,x0:x1]
    mask=cv2.inRange(cv2.cvtColor(roi,cv2.COLOR_BGR2HSV),np.array([0,0,190]),np.array([180,90,255]))
    contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);result=[]
    for c in contours:
        area=cv2.contourArea(c);x,y,cw,ch=cv2.boundingRect(c)
        if area<max(75,w*h*.00009) or cw<15 or ch<10 or not .3<=cw/ch<=6 or area/(cw*ch)<.56:continue
        q=cv2.approxPolyDP(c,.035*cv2.arcLength(c,True),True)
        if len(q)!=4 or not cv2.isContourConvex(q):continue
        m=cv2.getPerspectiveTransform(order_corners(q),np.float32([[0,0],[95,0],[95,127],[0,127]]));result.append((x,cv2.warpPerspective(roi,m,(96,128))))
    return [im for _,im in sorted(result,key=lambda v:v[0])]

records=metadata.get('trainingCrops') or json.loads((root/'training/v01-training-records.json').read_text('utf-8'))
for key in records:
    if key.startswith('fullcard-'):
        _,timestamp,role,index=key.split('-');timestamp=int(timestamp);index=int(index)
        path=research/f'full-{timestamp}.jpg';im=cv2.imread(str(path))
        if im is None:raise SystemExit('Missing '+str(path))
        if role=='dealer':
            region=[.47,.395,.62,.45] if timestamp==240 else [.46,.355,.60,.398]
        else:region=[.25,.37,.85,.55]
        cards=find_cards(im,region);out=research/(key+'.png')
        if index>=len(cards):raise SystemExit('Geometry differs for '+key+'; manually review crop/label.')
        q=order_corners(cards[index]['quad']);m=cv2.getPerspectiveTransform(q,np.float32([[0,0],[95,0],[95,127],[0,127]]));crop=cv2.warpPerspective(im,m,(96,128))
    else:
        name,frame,index=key.split('_');path=research/name/(frame+'.jpg');im=cv2.imread(str(path))
        if im is None:raise SystemExit('Missing '+str(path))
        cards=legacy_crops(im,regions[name]);index=int(index);out=research/'cards'/(key+'.png')
        if index>=len(cards):raise SystemExit('Geometry differs for '+key+'; manually review crop/label.')
        crop=cards[index]
    cv2.imwrite(str(out),crop);print(out.relative_to(root))
print('Review regenerated crops before training; timestamps/encoders can change pixels.')

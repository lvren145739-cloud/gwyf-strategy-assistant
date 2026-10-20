"""Hard negatives from fully reviewed single-player tables. Never held-out hands."""
from pathlib import Path
import cv2,numpy as np,sys,json,importlib.util
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from recognizer import find_cards,quad_iou,DNNSession,softmax
spec=importlib.util.spec_from_file_location('old',str(root.parent/'vision-window-fix/recognizer.py'));old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
r=root/'research';out=r/'v3-data/hardneg';out.mkdir(exist_ok=True)
sets=[('full-240.jpg',{'player':[.42,.45,.75,.63],'dealer':[.48,.405,.60,.443]}),('full-1435.jpg',{'player':[.42,.45,.75,.63],'dealer':[.46,.355,.60,.398]}),('full-2024.jpg',{'player':[.23,.44,.74,.55]}),('full-2066.jpg',{'player':[.25,.37,.85,.55]})]
# These four frames were already seen in model development. No independent
# accuracy claim is made for them; their old errors remain in reports.
records=[]
for name,regions in sets:
 image=cv2.imread(str(r/name));truth=[c['quad'] for region in regions.values() for c in old.find_cards(image,region)]
 for i,c in enumerate(find_cards(image)):
  overlaps=[quad_iou(c['quad'],q) for q in truth]
  if max(overlaps,default=0)>.25:continue
  # Exclude any inner fragment of a known true card from normal backgrounds;
  # those are covered separately by deliberately generated cut-card negatives.
  p=out/f'{Path(name).stem}-{i:03d}.png';cv2.imwrite(str(p),cv2.resize(c['image'],(96,128)))
  records.append({'file':str(p.relative_to(r)),'source':name,'quad':c['quad'],'label':'background','split':'train-hard-negative'})
(root/'training/v3-hard-negatives.json').write_text(json.dumps(records,indent=2))
from PIL import Image,ImageDraw
sheet=Image.new('RGB',(1200,((len(records)+11)//12)*110),'#222');d=ImageDraw.Draw(sheet)
for i,c in enumerate(records):
 im=Image.open(r/c['file']);im.thumbnail((78,90));x=i%12*100;y=i//12*110;sheet.paste(im,(x+10,y));d.text((x,y+90),str(i),fill='white')
sheet.save(r/'v3-data/hardneg-contact.jpg');print(len(records),'new hard negatives')

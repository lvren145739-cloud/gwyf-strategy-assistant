from pathlib import Path
import sys,json,importlib.util
import cv2,numpy as np
from PIL import Image,ImageDraw
r=Path('/workspace/vision-prototype/research');out=r/'v3-data';out.mkdir(exist_ok=True);(out/'candidates').mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('legacy',str(Path(__file__).resolve().parents[1]/'training/legacy_geometry.py'));legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
groups=[('bj-a',[13,16,19,22,25],[.35,.23,.85,.62]),('bj-b',[13,17,19,21],[.32,.27,.8,.6]),('poker-a',[7,10,13,17,19,33,37,40,41,53,57],[.20,.25,.95,.65]),('bili-cards',[17,18,22,23],[.01,.20,.95,.9])]
files=[(r/folder/f'{n:04d}.jpg' if folder!='bili-cards' else r/folder/f'{n:03d}.jpg',region) for folder,ns,region in groups for n in ns]
files += [(p,[0,0,1,1]) for p in sorted((r/'v3-frames').glob('*.jpg'))]
items=[]
for path,region in files:
 image=cv2.imread(str(path))
 if image is None:continue
 proposals=legacy.find_cards(image,region)
 # Wide new frames produce many UI quads; keep table-height candidates.
 if path.parent.name=='v3-frames':proposals=[c for c in proposals if c['rect'][1]>image.shape[0]*.20 and c['rect'][1]<image.shape[0]*.80 and c['rect'][0]>image.shape[1]*.03 and c['rect'][0]<image.shape[1]*.96]
 for index,c in enumerate(proposals):
  ident=f'{path.parent.name}-{path.stem}-{index:02d}';p=out/'candidates'/(ident+'.png');cv2.imwrite(str(p),c['image'])
  items.append({'id':ident,'file':str(p.relative_to(r)),'frame':str(path.relative_to(r)),'quad':c['quad'],'rect':c['rect'],'clipped':c['clipped']})
(out/'candidates.json').write_text(json.dumps(items,indent=2))
for page in range((len(items)+59)//60):
 subset=items[page*60:(page+1)*60];sheet=Image.new('RGB',(1200,((len(subset)+9)//10)*158),'#222');d=ImageDraw.Draw(sheet)
 for i,c in enumerate(subset):
  image=Image.open(r/c['file']);image.thumbnail((96,128));x=i%10*120;y=i//10*158;sheet.paste(image,(x+12,y));d.text((x,y+128),str(page*60+i)+' '+c['id'].split('-')[-2]+'-'+c['id'].split('-')[-1],fill='white')
 sheet.save(out/f'contact-{page}.jpg')
print(len(items),'candidates',flush=True)

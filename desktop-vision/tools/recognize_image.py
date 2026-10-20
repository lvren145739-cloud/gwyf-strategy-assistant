"""Reproducible single-image CLI; no GUI or screen capture required."""
import argparse,json,sys
from pathlib import Path
import cv2,numpy as np
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from recognizer import Recognizer
p=argparse.ArgumentParser();p.add_argument('image');p.add_argument('--regions',required=True,help='JSON file: {"player":[l,t,r,b],"dealer":[l,t,r,b]}');p.add_argument('--mode',choices=['blackjack','poker'],default='blackjack');p.add_argument('--output');args=p.parse_args()
im=cv2.imdecode(np.fromfile(args.image,dtype=np.uint8),cv2.IMREAD_COLOR)
if im is None:raise SystemExit('Cannot open image')
result=Recognizer().read(im,json.loads(Path(args.regions).read_text('utf-8')),args.mode)
for card in result['cards']:card.pop('preview',None)
s=json.dumps(result,ensure_ascii=False,indent=2)
if args.output:Path(args.output).write_text(s,'utf-8')
else:print(s)

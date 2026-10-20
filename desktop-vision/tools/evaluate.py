"""Development evaluation, NOT an independent estimate of production accuracy."""
import json,sys
from pathlib import Path
import cv2
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from recognizer import Recognizer
r=Recognizer();cases=[
 {'name':'front-blackjack','file':'full-240.jpg','mode':'blackjack','regions':{'player':[.42,.45,.75,.63],'dealer':[.48,.405,.60,.443]},'expected':[('player','5','hearts'),('player','2','hearts'),('dealer','9','clubs')],'trainingOverlap':True},
 {'name':'second-blackjack','file':'full-1435.jpg','mode':'blackjack','regions':{'player':[.42,.45,.75,.63],'dealer':[.46,.355,.60,.398]},'expected':[('player','Q','hearts'),('player','9','diamonds'),('dealer','3','hearts')],'trainingOverlap':'Dealer trained, player cards not trained'},
 {'name':'occluded-first-poker','file':'full-2024.jpg','mode':'poker','regions':{'player':[.38,.42,.93,.57]},'expected':[('player','A','hearts'),('player','7','clubs'),('player','8','clubs'),('player','2','diamonds'),('player','J','spades')],'trainingOverlap':True},
 {'name':'second-poker','file':'full-2066.jpg','mode':'poker','regions':{'player':[.25,.37,.85,.55]},'expected':[('player','6','diamonds'),('player','8','diamonds'),('player','6','clubs'),('player','8','spades'),('player','7','hearts')],'trainingOverlap':'6-diamonds trained; same-hand card checks are correlated'},
 {'name':'cross-video-clear-subregion','file':'bili-cards/022.jpg','mode':'poker','regions':{'player':[.67,.29,.845,.54]},'expected':[('player','7','clubs'),('player','9','spades'),('player','J','diamonds')],'trainingOverlap':False,'completeHand':False},
 {'name':'cross-video-extreme-angle','file':'bili-cards/025.jpg','mode':'poker','regions':{'player':[.01,.32,.15,.68]},'expected':[('player','Q','hearts'),('player','10','spades'),('player','10','clubs')],'trainingOverlap':False,'completeHand':False},
]
outputs=[]
for case in cases:
 path=root/'research'/case['file'];im=cv2.imread(str(path))
 if im is None:raise SystemExit('Research frame not found: '+str(path)+'; see DATA_SOURCES.md. Raw third-party frames are not shipped in the kit.')
 out=r.read(im,case['regions'],case['mode']);visible=[c for c in out['cards'] if not c['faceDown']]
 predicted=[(c['role'],c['rank'],c['suit']) for c in visible]
 exact=predicted==case['expected']
 clean=[{k:v for k,v in c.items() if k!='preview'} for c in out['cards']]
 outputs.append({**case,'predicted':predicted,'exactSelectedRegion':exact,'cards':clean,'recognitionMs':out['recognitionMs']})
report={'scope':'Six manually selected development cases. Cases overlap training and are not a random or blind validation sample. No population accuracy estimate. Cross-video clear subregion contains only 3 visible cards, not a complete poker hand.',
 'trainingVideo':'https://archive.org/details/pc-longplay-gamble-with-your-friends',
 'crossVideo':'https://www.bilibili.com/video/BV1XGVH6DEou/',
 'cases':outputs}
(root/'tests/vision-evaluation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps([{'name':c['name'],'exactSelectedRegion':c['exactSelectedRegion'],'predicted':c['predicted']} for c in outputs],ensure_ascii=False,indent=2))

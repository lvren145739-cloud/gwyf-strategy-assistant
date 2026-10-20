"""Same-input comparison; all selected development cases are reported, including failures."""
import json,sys,importlib.util,time
from pathlib import Path
import cv2
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from recognizer import Recognizer
old=ROOT.parent/'vision-prototype'
spec=importlib.util.spec_from_file_location('baseline',old/'recognizer.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
baseline=module.Recognizer();new=Recognizer()
cases=json.loads((old/'tests/vision-evaluation.json').read_text())['cases']
for c in cases:c['set']='legacy-regression'
cases += [
 {'name':'corrected-wide-poker-region','file':'full-2024.jpg','mode':'poker','regions':{'player':[.23,.44,.74,.55]},'expected':[('player','A','hearts'),('player','7','clubs'),('player','8','clubs'),('player','2','diamonds'),('player','J','spades')],'set':'corrected-input','note':'Legacy case excluded the entire first card by its ROI; BOTH models receive this same corrected ROI.'},
 {'name':'new-hand-club-three','file':'bili-cards/026.jpg','mode':'poker','regions':{'player':[.70,.42,.825,.615]},'expected':[('player','3','clubs')],'set':'not-trained-hand','note':'A separate hand, one fully visible card only. Not a complete poker hand.'},
 {'name':'new-video-duck-negative','file':'v2-unseen/001.jpg','mode':'poker','regions':{'player':[.25,.45,.75,.70]},'expected':[],'set':'new-video-negative','note':'Independent video has ducks, not cards. Never used in training.'}]
rows=[]
for case in cases:
 im=cv2.imread(str(ROOT/'research'/case['file']))
 if im is None:continue
 row={k:case[k] for k in ['name','file','mode','regions','expected','set']}
 if 'note' in case:row['note']=case['note']
 expected=[list(x) for x in case['expected']]
 for tag,model in [('v01',baseline),('v02',new)]:
  t=time.perf_counter();out=model.read(im,case['regions'],case['mode']);cards=[c for c in out['cards'] if not c['faceDown']];prediction=[[c['role'],c['rank'],c['suit']] for c in cards]
  row[tag]={'exact':prediction==expected,'predicted':prediction,'milliseconds':round((time.perf_counter()-t)*1000,2),'reviews':sum(c['review'] for c in cards),'details':[{k:v for k,v in c.items() if k!='preview'} for c in cards]}
 rows.append(row)
report={'scope':'Selected development examples, NOT an accuracy estimate. Several regression cases overlap training; the legacy cropped-ROI case is retained unchanged and has a separate corrected-input case. New held-out hand has only one visible card; new video provides a negative example only.','cases':rows,'summary':{tag:{'exactCases':sum(c[tag]['exact'] for c in rows),'totalCases':len(rows)} for tag in ['v01','v02']}}
(ROOT/'tests/model-comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps({'summary':report['summary'],'cases':[{k:c[k] for k in ['name','set']}|{tag:{'exact':c[tag]['exact'],'predicted':c[tag]['predicted'],'reviews':c[tag]['reviews']} for tag in ['v01','v02']} for c in rows]},ensure_ascii=False,indent=2))

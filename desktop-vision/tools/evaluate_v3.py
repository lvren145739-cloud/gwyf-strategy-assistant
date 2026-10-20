"""Development comparison, held-out hands and negative-image checks.
Never reports a selected-case ratio as overall in-game accuracy.
"""
from pathlib import Path
import sys,json,cv2,numpy as np,importlib.util,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from recognizer import Recognizer
spec=importlib.util.spec_from_file_location('baseline',str(ROOT.parent/'vision-window-fix/recognizer.py'));old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
new=Recognizer();baseline=old.Recognizer(ROOT.parent/'vision-window-fix/models');R=ROOT/'research'
cases=json.loads((ROOT/'tests/model-comparison.json').read_text())['cases'];records=[]
def visible(out):return sorted([[c.get('role'),c.get('rank'),c.get('suit')] for c in out['cards'] if not c.get('faceDown')],key=lambda x:str(x))
def clean(out):
 for c in out['cards']:c.pop('preview',None)
 return out
for c in cases:
 im=cv2.imread(str(R/c['file']));o=baseline.read(im,c['regions'],c['mode']);n=new.read(im,c['regions'],c['mode']);expected=sorted(c['expected'],key=lambda x:str(x))
 rec={'name':c['name'],'file':c['file'],'mode':c['mode'],'regions':c['regions'],'expected':expected,'v02':{'exact':visible(o)==expected,'predicted':visible(o)},'v03':{'exact':visible(n)==expected,'predicted':visible(n),'autoReady':n['autoReady'],'details':clean(n)}}
 records.append(rec);print(c['name'],'exact',rec['v03']['exact'],'auto',n['autoReady'],visible(n),flush=True)
fulls=[('full-240.jpg','blackjack',[['player','5','hearts'],['player','2','hearts'],['dealer','9','clubs']]),('full-1435.jpg','blackjack',[['player','Q','hearts'],['player','9','diamonds'],['dealer','3','hearts']]),('full-2024.jpg','poker',[['player','A','hearts'],['player','7','clubs'],['player','8','clubs'],['player','2','diamonds'],['player','J','spades']]),('full-2066.jpg','poker',[['player','6','diamonds'],['player','8','diamonds'],['player','6','clubs'],['player','8','spades'],['player','7','hearts']]),('poker-a/0057.jpg','poker',[['player','A','diamonds'],['player','9','diamonds'],['player','5','clubs'],['player','2','hearts'],['player','K','spades']])]
full_records=[]
for file,mode,expected in fulls:
 im=cv2.imread(str(R/file));out=new.read(im,{},mode);exact=visible(out)==sorted(expected,key=lambda x:str(x))
 rec={'file':file,'mode':mode,'expected':expected,'exact':exact,'predicted':visible(out),**clean(out)};full_records.append(rec)
 print('AUTO',file,'exact',exact,'ready',out['autoReady'],visible(out),flush=True)
synthetic=[]
for case in json.loads((ROOT/'tests/reconstructed-cases.json').read_text()):
 out=new.read(cv2.imread(str(R/case['file'])),{},'blackjack');exact=visible(out)==sorted(case['expected'],key=lambda x:str(x));synthetic.append({**case,'exact':exact,'predicted':visible(out),**clean(out)})
 print('RECONSTRUCTED',case['name'],'exact',exact,'ready',out['autoReady'],visible(out),flush=True)
negatives=[]
for n in [1,3,4,7,8,9,10,11,12,13,14,15,16,17,18,19,20]:
 path=R/'v2-unseen'/f'{n:03d}.jpg';regions={'player':[.25,.45,.75,.7]} if n==1 else {}
 out=new.read(cv2.imread(str(path)),regions,'poker');pred=visible(out);negatives.append({'file':str(path.relative_to(R)),'predicted':pred,'autoReady':out['autoReady'],'detected':len(pred),'details':clean(out)})
 print('NEGATIVE',n,len(pred),out['autoReady'],flush=True)
report={'scope':'Selected development cases, including trained/previously inspected scenes; not an independent or overall accuracy estimate. Reconstructed cases are synthetic, not user attachment pixels.','comparison':records,'automaticFullTables':full_records,'syntheticReportedLayouts':synthetic,'negativeScenes':negatives,'summary':{'oldExact':sum(c['v02']['exact'] for c in records),'newExact':sum(c['v03']['exact'] for c in records),'comparisonCases':len(records),'fullTableExact':sum(c['exact'] for c in full_records),'fullTableAuto':sum(c['autoReady'] for c in full_records),'fullTableCases':len(full_records),'syntheticExact':sum(c['exact'] for c in synthetic),'syntheticAuto':sum(c['autoReady'] for c in synthetic),'negativeScenes':len(negatives),'negativeAutomaticCalculations':sum(c['autoReady'] for c in negatives),'incorrectFullTableAutomaticCalculations':sum(c['autoReady'] and not c['exact'] for c in full_records)}}
(ROOT/'tests/v3-evaluation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8');print(json.dumps(report['summary']),flush=True)

"""Truth-labelled visible-card regressions under the installed target runtime."""
from pathlib import Path
import sys,json,cv2
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root));from recognizer import Recognizer
r=Recognizer();cases=json.loads((root/'tests/model-comparison.json').read_text())['cases'];results=[]
required={'front-blackjack','second-blackjack','second-poker','cross-video-clear-subregion','cross-video-extreme-angle','corrected-wide-poker-region','new-hand-club-three'}
for c in cases:
 out=r.read(cv2.imread(str(root/'research'/c['file'])),c['regions'],c['mode']);visible=[x for x in out['cards'] if not x['faceDown']];pred=[[x['role'],x['rank'],x['suit']] for x in visible];exact=sorted(pred,key=str)==sorted(c['expected'],key=str)
 if c['name'] in required:assert exact,(c['name'],pred)
 if c['name']=='new-video-duck-negative':assert all(x['rank'] is None and x['review'] for x in visible)
 if c['name']=='occluded-first-poker':assert not out['autoReady'], 'Clipped/incomplete hand must never calculate automatically'
 results.append({'name':c['name'],'exact':exact,'predicted':pred})
print(json.dumps({'python':sys.version.split()[0],'opencv':cv2.__version__,'truthChecks':len(required),'negativeAbstention':True,'clippedAbstention':True,'cases':results},ensure_ascii=False))

"""Run with each supported interpreter; no screen/GPU/GUI required."""
import sys,json,hashlib,tempfile,shutil
from pathlib import Path
import cv2,numpy as np,mss,webview
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root));sys.path.insert(0,str(root/'tools'))
from recognizer import Recognizer
from app import API
from setup_runtime import supported
assert supported({'version':[3,15],'bits':64,'gilDisabled':False,'machine':'AMD64'})
assert not supported({'version':[3,15],'bits':64,'gilDisabled':True,'machine':'AMD64'})
assert not supported({'version':[3,16],'bits':64,'gilDisabled':False,'machine':'AMD64'})
assert not supported({'version':[3,14],'bits':32,'gilDisabled':False,'machine':'AMD64'})
r=Recognizer();im=cv2.imread(str(root/'research/full-240.jpg'))
regions={'player':[.42,.45,.75,.63],'dealer':[.48,.405,.60,.443]}
out=r.read(im,regions);visible=[(c['rank'],c['role']) for c in out['cards'] if not c['faceDown']]
assert visible==[('5','player'),('2','player'),('9','dealer')],visible
assert out['hiddenCount']==1;json.dumps(out)
for c in out['cards']:c.pop('preview',None)
out.pop('recognitionMs',None)
with tempfile.TemporaryDirectory(prefix='识牌兼容性-') as folder:
 for name in ['rank.onnx','suit.onnx']:shutil.copyfile(root/'models'/name,Path(folder)/name)
 alt=Recognizer(folder);a=alt.rank.run(None,{'image':np.zeros((2,1,48,48),np.float32)})[0];assert a.shape==(2,15);assert np.isfinite(a).all()
api=API();api.frame=im;json.dumps(api.recognize(regions,'blackjack'));assert 'python' in api.status()
print(json.dumps({'python':sys.version.split()[0],'numpy':np.__version__,'opencv':cv2.__version__,'backend':r.backend,'visible':visible,'unicodePath':True,'jsonBridge':True,'freeThreadGuard':True,'recognitionDigest':hashlib.sha256(json.dumps(out,sort_keys=True).encode()).hexdigest()}))

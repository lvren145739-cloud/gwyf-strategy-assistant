import json,sys,time,resource
from pathlib import Path
import numpy as np,cv2
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from recognizer import Recognizer
p=root/'research/full-240.jpg';im=cv2.imread(str(p));regions={'player':[.42,.45,.75,.63],'dealer':[.48,.405,.60,.443]}
t=time.perf_counter();r=Recognizer();load=(time.perf_counter()-t)*1000
r.read(im,regions)
times=[]
for _ in range(100):
 t=time.perf_counter();o=r.read(im,regions);times.append((time.perf_counter()-t)*1000)
result={'cpu':'AMD EPYC 7763, container 3 vCPU, OpenCV DNN 1 thread',
 'runtime':{'backend':'OpenCV DNN','opencv':cv2.__version__,'numpy':np.__version__},
 'image':[int(im.shape[1]),int(im.shape[0])],'iterations':len(times),
 'modelLoadMs':round(load,2),'recognitionP50Ms':round(float(np.median(times)),2),
 'recognitionP95Ms':round(float(np.percentile(times,95)),2),
 'processPeakRssMiB':round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,1),
 'modelBytes':sum(p.stat().st_size for p in (root/'models').glob('*.onnx')),
 'scope':'Image already in memory. Includes contour detection, glyph inference and card previews. Excludes screen capture, desktop shell, confirmation and decision solver. Linux process RSS is not Windows overlay RSS.'}
(root/'tests/benchmark.json').write_text(json.dumps(result,indent=2),'utf-8');print(json.dumps(result,indent=2))

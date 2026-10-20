import urllib.request,json,concurrent.futures
from pathlib import Path
names=['numpy','opencv-python-headless','onnxruntime','pywebview','pythonnet','mss']
def read(name):
 x=json.load(urllib.request.urlopen('https://pypi.org/pypi/'+name+'/json',timeout=40));info=x['info']
 files=[v['filename'] for v in x['urls'] if ('win_amd64' in v['filename'] or 'none-any' in v['filename'])]
 return name,{'version':info['version'],'requires_python':info['requires_python'],'requires_dist':info.get('requires_dist'),'windowsFiles':files}
with concurrent.futures.ThreadPoolExecutor(6) as ex:result=dict(ex.map(read,names))
(Path(__file__).resolve().parents[1]/'tests/pypi-support.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))

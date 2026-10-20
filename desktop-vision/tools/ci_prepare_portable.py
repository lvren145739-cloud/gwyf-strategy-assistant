"""Assemble a real embedded runtime on the Windows test runner (no system install).
The downloaded Python archive is pinned to the same SHA as the shipped bundle.
"""
from pathlib import Path
import urllib.request,zipfile,hashlib,subprocess,sys,json
ROOT=Path(__file__).resolve().parents[1];target=ROOT/'runtime'
info=json.loads((ROOT/'tools/python-source.json').read_text('utf-8'));p=ROOT/'python-embedded.zip'
with urllib.request.urlopen(info['url'],timeout=90) as source:p.write_bytes(source.read())
assert hashlib.sha256(p.read_bytes()).hexdigest()==info['sha256']
with zipfile.ZipFile(p) as z:z.extractall(target)
site=target/'Lib/site-packages'
subprocess.run([sys.executable,'-m','pip','install','--disable-pip-version-check','--no-compile','--target',str(site),'numpy==2.5.4','opencv-python-headless==5.0.0.93','mss==10.2.0','pywebview==6.2.1','pythonnet==3.2.1'],check=True)
(target/'python314._pth').write_text('python314.zip\n.\nLib/site-packages\n..\nimport site\n','utf-8')
print('Embedded Windows Python and dependencies assembled.')

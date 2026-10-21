"""Build and publish the self-contained Windows package from pinned sources."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,urllib.request
ROOT=Path(__file__).resolve().parents[1];BUILD=ROOT.parent/'vision-v3-build'
BUILD.mkdir(exist_ok=True)
info=json.loads((ROOT/'tools/python-source.json').read_text())
shutil.copyfile(ROOT/'python-embedded.zip',BUILD/'python-3.14.8-embed-amd64.zip')
shutil.copyfile(ROOT/'tools/python-source.json',BUILD/'python-source.json')
info=json.loads((ROOT/'tools/webview2-offline-source.json').read_text())
installer=BUILD/'MicrosoftEdgeWebView2RuntimeInstallerX64.exe'
with urllib.request.urlopen(info['url'],timeout=180) as response,installer.open('wb') as output:
 shutil.copyfileobj(response,output)
assert hashlib.sha256(installer.read_bytes()).hexdigest()==info['sha256'],'Microsoft installer hash changed; do not run or publish'
shutil.copyfile(ROOT/'tools/webview2-offline-source.json',BUILD/'webview2-offline-source.json')
wheels=BUILD/'wheels'
subprocess.run([sys.executable,'-m','pip','wheel','--wheel-dir',str(wheels),'--requirement',str(ROOT/'tests/windows-locks/python314.txt')],check=True)
for script in ['build_preview.py','build_portable.py','build_package.py']:
 subprocess.run([sys.executable,str(ROOT/'tools'/script)],check=True)
portable=BUILD/'GWYF-Vision-0.3.2-Windows'
subprocess.run([str(portable/'runtime/python.exe'),'-c',"import app,hotkeys,recognizer,cv2,numpy,webview,clr; clr.AddReference('System.Windows.Forms'); assert app.VERSION=='0.3.2'; assert hotkeys.DEFAULTS['reset']=='F11'; assert hotkeys.DEFAULTS['discard']=='F7'; recognizer.Recognizer(); print('Actual portable runtime, shortcut module and six models passed')"],cwd=portable,check=True)
files=[ROOT.parent/'GWYF-Vision-0.3.2-Windows-Portable.zip',ROOT.parent/'GWYF-Vision-0.3.2.zip']
checksums=ROOT.parent/'GWYF-Vision-0.3.2-SHA256SUMS.txt'
checksums.write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in files),encoding='utf-8')
subprocess.run(['gh','release','create','vision-v0.3.2',*[str(p) for p in files],str(checksums),'--target','desktop-vision-v0.3','--prerelease','--title','GWYF Vision 0.3.2 - Windows portable and automatic decisions','--notes-file',str(ROOT/'RELEASE.md')],check=True)

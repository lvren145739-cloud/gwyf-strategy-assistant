"""Build a Windows x64 embedded-Python distribution without system installation.
Uses downloaded official Python archive and target-specific binary wheels.
"""
from pathlib import Path
import hashlib,json,shutil,zipfile
ROOT=Path(__file__).resolve().parents[1];BUILD=ROOT.parent/'vision-v3-build';DIST=BUILD/'GWYF-Vision-0.3.2-Windows';RUNTIME=DIST/'runtime'

def extract_wheel(path,dest):
 with zipfile.ZipFile(path) as wheel:
  for info in wheel.infolist():
   if info.is_dir():continue
   name=Path(info.filename)
   if name.is_absolute() or '..' in name.parts:raise ValueError('Unsafe wheel path')
   if '.data' in name.parts[0]:
    scheme=name.parts[1]
    if scheme not in ('purelib','platlib'):continue
    name=Path(*name.parts[2:])
   target=dest/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(wheel.read(info))

def main():
 DIST.mkdir(parents=True,exist_ok=True);RUNTIME.mkdir(exist_ok=True)
 with zipfile.ZipFile(BUILD/'python-3.14.8-embed-amd64.zip') as z:z.extractall(RUNTIME)
 site=RUNTIME/'Lib/site-packages';site.mkdir(parents=True,exist_ok=True)
 for p in sorted((BUILD/'wheels').glob('*.whl')):extract_wheel(p,site)
 (RUNTIME/'python314._pth').write_text('python314.zip\n.\nLib/site-packages\n..\nimport site\n','utf-8')
 # Whole source/models, but never developer videos, training caches or virtualenvs.
 for name in ['app.py','recognizer.py','hotkeys.py','portable-launch.py','LICENSE','NOTICE.md','README.md','CHANGELOG.md','DATA_SOURCES.md']:
  shutil.copyfile(ROOT/name,DIST/name)
 for folder in ['web','models']:
  target=DIST/folder
  if target.exists():shutil.rmtree(target)
  shutil.copytree(ROOT/folder,target,ignore=shutil.ignore_patterns('preview-test.html','__pycache__','*.log'))
 validation=DIST/'validation';validation.mkdir(exist_ok=True)
 for name in ['VALIDATION.md','windows-native-results.json','v3-evaluation.json','python-compatibility.json','benchmark.json','four-evaluation.json','shortcuts-results.json','poker-shortcut-results.json']:
  shutil.copyfile(ROOT/'tests'/name,validation/name)
 support=DIST/'runtime-support';support.mkdir(exist_ok=True)
 for name in ['MicrosoftEdgeWebView2RuntimeInstallerX64.exe','webview2-offline-source.json','python-source.json']:shutil.copyfile(BUILD/name,support/name)
 # Windows Script Host is present on ordinary Win10/11. CMD alternative is also
 # provided for managed computers with WSH disabled. Neither needs administrator.
 vbs='''Option Explicit
Dim shell, files, root, python, command
Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
root = files.GetParentFolderName(WScript.ScriptFullName)
python = root & "\\runtime\\pythonw.exe"
If Not files.FileExists(python) Then
  MsgBox "Please extract the entire ZIP, then launch again.", 16, "GWYF Vision"
  WScript.Quit 1
End If
shell.CurrentDirectory = root
command = Chr(34) & python & Chr(34) & " " & Chr(34) & root & "\\portable-launch.py" & Chr(34)
shell.Run command, 1, False
'''
 (DIST/'启动识牌助手.vbs').write_bytes(vbs.replace('\n','\r\n').encode('ascii'))
 cmd='''@echo off
setlocal
cd /d "%~dp0"
if not exist "runtime\\python.exe" (
 echo Please extract the entire ZIP before launching.
 pause
 exit /b 1
)
"runtime\\python.exe" "portable-launch.py"
if errorlevel 1 pause
'''
 (DIST/'启动识牌助手.cmd').write_bytes(cmd.replace('\n','\r\n').encode('ascii'))
 (DIST/'使用说明.txt').write_text('GWYF Vision 0.3.2 — Windows 10/11 x64\n\n1. 完整解压。\n2. 双击“启动识牌助手.cmd”；也可用.vbs静默启动。\n3. 选择游戏窗口，F7 在助手内确认推荐换牌（游戏中仍需手动换牌），按 F8 截一帧，F9 归档，F10 采用核对草稿，F11 重置牌堆（可撤销）。点击页头“快捷键”可以修改五项按键并保存。默认自动找牌，可靠且完整的牌面直接计算建议。\n\n随包包含Python、运行依赖和本地模型，不用安装Python或运行pip。缺少微软WebView2时，首次启动会使用包内微软离线安装器准备，无需联网。\n没有修改系统Python，不需要管理员权限。\n牌区不再是截图裁切边界；可自动找牌，也可手动校准归属。\n误判或漏牌仍可能发生：疑点会显示可修正草稿；自动结果也可以改牌或撤销。归档仍需主动点击或按快捷键。\n本机存档：%LOCALAPPDATA%\\GWYF-Vision-Prototype\\state.json\n启动日志：同目录startup.log。快捷键独立保存在hotkeys.json，不受手牌撤销影响。\n\nCreated by lvren with GPT-6.1Sol.\n本项目源码和自训练模型为MIT；随包第三方运行库保留各自许可，详见runtime/LICENSE.txt、各包dist-info/licenses和NOTICE.md。\n','utf-8-sig')
 sources=[]
 for p in sorted((BUILD/'wheels').glob('*.whl')):sources.append({'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size})
 (DIST/'runtime-support/wheels.json').write_text(json.dumps(sources,indent=2),'utf-8')
 files=[p for p in sorted(DIST.rglob('*')) if p.is_file() and p.name!='SHA256SUMS.txt']
 manifest=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(DIST).as_posix()+'\n' for p in files)
 (DIST/'SHA256SUMS.txt').write_text(manifest,'utf-8');files.append(DIST/'SHA256SUMS.txt')
 output=ROOT.parent/'GWYF-Vision-0.3.2-Windows-Portable.zip'
 with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=7) as z:
  for p in files:z.write(p,DIST.name+'/'+p.relative_to(DIST).as_posix())
 with zipfile.ZipFile(output) as z:
  assert z.testzip() is None
  for line in manifest.splitlines():
   digest,path=line.split('  ',1)
   assert hashlib.sha256(z.read(DIST.name+'/'+path)).hexdigest()==digest,path
 print(output.name.encode('ascii','backslashreplace').decode('ascii'),output.stat().st_size,hashlib.sha256(output.read_bytes()).hexdigest(),len(files),'files')

if __name__=='__main__':main()

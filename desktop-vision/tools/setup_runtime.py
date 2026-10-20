"""Stdlib-only bootstrap: discover supported Windows Python, create isolated venv.
Never deletes an existing environment or alters the system Python installation.
"""
import argparse,json,os,platform,struct,subprocess,sys,sysconfig
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SUPPORTED=(15,14,13,12,11)
PROBE="import sys,sysconfig,struct,json,platform;print(json.dumps({'exe':sys.executable,'version':list(sys.version_info[:2]),'bits':struct.calcsize('P')*8,'gilDisabled':bool(sysconfig.get_config_var('Py_GIL_DISABLED')),'machine':platform.machine()}))"

def supported(info):
 return info.get('version',[0,0])[0]==3 and info['version'][1] in SUPPORTED and info.get('bits')==64 and not info.get('gilDisabled',False) and info.get('machine','').lower() in ('amd64','x86_64')

def discover(explicit=None):
 commands=[[explicit]] if explicit else [[sys.executable]]+[['py','-3.'+str(n)] for n in SUPPORTED]+[['python']]
 found={}
 for command in commands:
  try:
   p=subprocess.run(command+['-c',PROBE],capture_output=True,text=True,timeout=12)
   info=json.loads(p.stdout.strip())
   if p.returncode==0 and supported(info):found[os.path.normcase(info['exe'])]=info
  except (OSError,ValueError,subprocess.TimeoutExpired):pass
 return sorted(found.values(),key=lambda r:r['version'],reverse=True)

def run(command):
 print('Running:',subprocess.list2cmdline([str(c) for c in command]),flush=True)
 subprocess.run([str(c) for c in command],check=True)

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--python',help='Use this Python executable');parser.add_argument('--list',action='store_true');args=parser.parse_args()
 options=discover(args.python)
 if args.list:print(json.dumps(options,indent=2));return
 if os.name!='nt':raise SystemExit('The desktop installer is for Windows x64. Linux inference tests can install requirements.txt directly.')
 if not options:raise SystemExit('No supported standard CPython x64 found. Install Python 3.11-3.15 x64 (not the free-threaded t build), then retry. https://www.python.org/downloads/windows/')
 chosen=options[0];minor=chosen['version'][1];folder=ROOT/('.venv-py3'+str(minor));python=folder/'Scripts/python.exe';ready=folder/'gwyf-ready.json'
 if ready.exists():ready.unlink()  # Only the readiness marker; environment/data are preserved.
 if not python.exists():run([chosen['exe'],'-m','venv',folder])
 info=json.loads(subprocess.check_output([str(python),'-c',PROBE],text=True))
 if not supported(info) or info['version']!=chosen['version']:raise SystemExit('Existing environment uses a different interpreter. Use a new extracted folder; no files have been deleted.')
 run([python,'-m','pip','install','--upgrade','pip'])
 run([python,'-m','pip','install','--prefer-binary','--only-binary=numpy,opencv-python-headless,pythonnet,cffi,clr_loader','-r',ROOT/'requirements.txt'])
 run([python,ROOT/'tools/check_install.py'])
 ready.write_text(json.dumps({'project':'GWYF Vision','version':'0.3.0','python':info},indent=2),'utf-8')
 print('\nReady. Run Start-Windows.bat. State in LOCALAPPDATA is preserved.')

if __name__=='__main__':main()

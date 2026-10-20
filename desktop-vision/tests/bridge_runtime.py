"""Check actual pywebview RPC registration without starting a GUI."""
from pathlib import Path
import json,re,sys,time
from importlib.metadata import version
import webview,webview.util as util
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import API,DesktopBridge
controller=API()
w=webview.create_window('RPC registration check','about:blank',js_api=DesktopBridge(controller))
controller.window=w
w.js_api_endpoint=None
scripts=[]
w.run_js=lambda code:scripts.append(code)
started=time.perf_counter()
util.inject_pywebview('edgechromium',w)
assert w.events._pywebviewready.wait(2),'Desktop bridge registration timed out'
assert len(scripts)==2
funcs=json.loads(re.search(r"JSON.parse\('(.*)'\)",scripts[1]).group(1))
expected={'status','windows','select_window','capture','open_image','recognize','load_state','save_state','compact'}
assert {f['func'] for f in funcs}==expected
print(json.dumps({'python':sys.version.split()[0],'pywebview':version('pywebview'),'methods':len(funcs),'injectionMs':round((time.perf_counter()-started)*1000,2),'scope':'real API registration only; no GUI or Win32 capture'},ensure_ascii=False))

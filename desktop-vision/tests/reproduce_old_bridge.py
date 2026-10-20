"""Demonstrate the old public Window exposure stalling real bridge injection.
No GUI or native capture is mocked as having passed by this demonstration.
"""
import sys, threading, traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app, webview, webview.util as util
api=app.API()
w=webview.create_window('repro','about:blank',js_api=api)
api.window=w
scripts=[]
w.run_js=lambda code:scripts.append(code)
util.load_js_files=lambda window,platform:('/* bootstrap */','%(functions)s')
threads=[]
def daemon_thread(*args,**kwargs):
    t=threading.Thread(*args,**kwargs,daemon=True);threads.append(t);return t
util.Thread=daemon_thread
util.inject_pywebview('edgechromium',w)
threads[0].join(.3)
assert not w.events._pywebviewready.is_set()
assert len(scripts)==1
print('OLD: bootstrap injected, API creation stalled while scanning public Window.')
traceback.print_stack(sys._current_frames()[threads[0].ident],limit=7)

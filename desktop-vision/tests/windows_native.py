"""Real Windows/WebView2/Win32 test with our own visible test window.
This is not a test against the user's game process or their screen photos.
"""
from pathlib import Path
import ctypes,json,os,sys,threading,time,traceback
from ctypes import wintypes
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import webview
from app import API,DesktopBridge,TITLE
assert os.name=='nt'
api=API();report={'platform':sys.platform,'python':sys.version.split()[0]};error=[]
app=webview.create_window(TITLE,str(ROOT/'web/desktop.html'),js_api=DesktopBridge(api),width=560,height=820,x=700,y=30)
api.window=app
fixture=webview.create_window('Gamble With Your Friends - test fixture',html='<html><body style="background:#315f42;color:white;font:40px Arial">Native capture fixture<div style="background:white;color:black">9 clubs / 8 clubs / A hearts</div></body></html>',width=640,height=450,x=20,y=30)

def test():
 try:
  assert app.events.loaded.wait(35),'WebView2 page did not load'
  assert fixture.events.shown.wait(15),'Fixture window not shown'
  names=app.evaluate_js('Object.keys(window.pywebview.api).sort()')
  assert names==sorted(['status','windows','select_window','capture','open_image','recognize','load_state','save_state','compact']),names
  report['realWebView2Bridge']=True
  rows=app.evaluate_js('window.pywebview.api.windows()')
  report['enumeratedTitles']=[r['title'] for r in rows]
  target_hwnd=int(fixture.native.Handle.ToInt64())
  report['fixtureHandle']=str(target_hwnd)
  report['fixtureVisible']=bool(api.native.user.IsWindowVisible(target_hwnd))
  n=api.native.user.GetWindowTextLengthW(target_hwnd);buf=ctypes.create_unicode_buffer(n+1);api.native.user.GetWindowTextW(target_hwnd,buf,n+1);report['fixtureNativeTitle']=buf.value
  target=next(r for r in rows if r['id']==str(target_hwnd))
  assert not any(r['title']==TITLE for r in rows)
  assert isinstance(target['id'],str)
  report['nativeEnumWindows']=True
  assert app.evaluate_js('window.pywebview.api.select_window('+json.dumps(target['id'])+')')
  status=app.evaluate_js('window.pywebview.api.status()');assert status['version']=='0.3.0';assert status['native']
  report['statusRPC']=True
  # Verify actual own-window capture only if this runner has foreground focus.
  hwnd=int(target['id']);api.native.user.SetForegroundWindow.argtypes=[wintypes.HWND]
  api.native.user.SetForegroundWindow(hwnd);time.sleep(.4)
  foreground=api.native.user.GetAncestor(api.native.user.GetForegroundWindow(),2)
  if foreground==hwnd:
   out=api.capture();assert out['width']>200 and out['height']>150 and out['image'].startswith('data:image/png;base64,')
   report['mssOwnWindowCapture']={'width':out['width'],'height':out['height']}
  else:report['mssOwnWindowCapture']={'skipped':'runner did not grant foreground focus'}
  report['scope']='Windows native GUI and synthetic own-window capture. No real game run.'
 except Exception:
  error.append(traceback.format_exc());report['error']=error[-1]
 finally:
  dest=ROOT/'tests/windows-native-results.json';dest.write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8');print(json.dumps(report,ensure_ascii=False),flush=True)
  try:fixture.destroy()
  except Exception:pass
  try:app.destroy()
  except Exception:pass

webview.start(test,gui='edgechromium',private_mode=True,http_server=True)
if error:raise SystemExit(1)

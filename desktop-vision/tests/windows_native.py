"""Real Windows/WebView2/Win32 test with our own visible test window.
This is not a test against the user's game process or their screen photos.
"""
from pathlib import Path
import ctypes,json,os,sys,threading,time,traceback,tempfile
from ctypes import wintypes
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import webview
from app import API,DesktopBridge,TITLE
assert os.name=='nt'
import importlib.util
spec=importlib.util.spec_from_file_location('portable_launcher',ROOT/'portable-launch.py')
launcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(launcher)
assert launcher.webview2_installed(),'Portable launcher must detect the installed WebView2 runtime'
api=API();report={'platform':sys.platform,'python':sys.version.split()[0],'portableWebView2Detection':True};error=[]
app=webview.create_window(TITLE,str(ROOT/'web/desktop.html'),js_api=DesktopBridge(api),width=560,height=820,x=700,y=30)
api.window=app
fixture=webview.create_window('Gamble With Your Friends - test fixture',html='<html><body style="background:#315f42;color:white;font:40px Arial">Native capture fixture<div style="background:white;color:black">9 clubs / 8 clubs / A hearts</div></body></html>',width=640,height=450,x=20,y=30)
from hotkeys import HotkeyManager,DEFAULTS
hotkey_folder=tempfile.TemporaryDirectory(prefix='gwyf-hotkey-native-')
actions=[]
api.hotkey_manager=HotkeyManager(api.native.user,actions.append,Path(hotkey_folder.name)/'hotkeys.json')
api.hotkey_manager.start()
assert api.hotkey_manager.ready.wait(3)

def rpc(script):
 # pywebview.evaluate_js returns resolved Promises ONLY via callback, not the
 # direct return value. Inspecting that direct value tested {} instead of rows.
 done=threading.Event();values=[]
 def receive(value):values.append(value);done.set()
 app.evaluate_js(script,callback=receive)
 assert done.wait(15),'RPC timed out: '+script
 return values[0]

def test():
 try:
  assert app.events.loaded.wait(35),'WebView2 page did not load'
  assert fixture.events.shown.wait(15),'Fixture window not shown'
  names=app.evaluate_js('Object.keys(window.pywebview.api).sort()')
  assert names==sorted(['status','windows','select_window','capture','open_image','recognize','load_state','save_state','compact','hotkeys']),names
  report['realWebView2Bridge']=True
  rows=rpc('window.pywebview.api.windows()')
  target_hwnd=int(fixture.native.Handle.ToInt64())
  target=next(r for r in rows if r['id']==str(target_hwnd))
  assert not any(r['title']==TITLE for r in rows)
  assert isinstance(target['id'],str)
  report['nativeEnumWindows']=True
  assert rpc('window.pywebview.api.select_window('+json.dumps(target['id'])+')')
  status=rpc('window.pywebview.api.status()');assert status['version']=='0.3.1';assert status['native']
  report['statusRPC']=True
  # Register and reconfigure real global keys on the dedicated message thread.
  keys=rpc("window.pywebview.api.hotkeys({op:'get'})")
  assert keys['config']==DEFAULTS
  custom={'capture':'F13','archive':'F14','accept':'F15','reset':'F16'}
  result=rpc('window.pywebview.api.hotkeys('+json.dumps({'op':'set','config':custom})+')')
  assert all(result['registered'].values())
  assert json.loads((Path(hotkey_folder.name)/'hotkeys.json').read_text())==custom
  # A conflicting combination in another thread must leave all old keys alive.
  user=api.native.user
  assert user.RegisterHotKey(None,9001,0x4007,0x87)  # Ctrl+Alt+Shift+F24
  try:
   conflict={**custom,'capture':'Ctrl+Alt+Shift+F24'}
   failed=rpc('window.pywebview.api.hotkeys('+json.dumps({'op':'set','config':conflict})+").then(()=>({failed:false}),e=>({failed:true,message:String(e)}))")
   assert failed['failed']
   after=rpc("window.pywebview.api.hotkeys({op:'get'})")
   assert after['config']==custom and all(after['registered'].values())
  finally:user.UnregisterHotKey(None,9001)
  paused=rpc("window.pywebview.api.hotkeys({op:'pause'})")
  assert paused['paused'] and not any(paused['registered'].values())
  assert user.RegisterHotKey(None,9002,0x4000,0x7C)  # F13 temporarily released
  user.UnregisterHotKey(None,9002)
  for _ in range(2):
   resumed=rpc("window.pywebview.api.hotkeys({op:'resume'})")
   assert all(resumed['registered'].values())
  # Deliver actual Windows keyboard events; MOD_NOREPEAT rejects repeated down.
  user.keybd_event.argtypes=[wintypes.BYTE,wintypes.BYTE,wintypes.DWORD,ctypes.c_size_t]
  before=len(actions)
  for key in [0x7C,0x7D,0x7E,0x7F]:
   user.keybd_event(key,0,0,0);time.sleep(.035)
   user.keybd_event(key,0,0,0);time.sleep(.035)
   user.keybd_event(key,0,2,0)
  deadline=time.monotonic()+3
  while len(actions)<before+4 and time.monotonic()<deadline:time.sleep(.02)
  assert actions[before:]==['capture','archive','accept','reset'],actions
  api.hotkey_manager.active=lambda:False
  time.sleep(.12)
  assert not api.hotkey_manager.registered
  assert user.RegisterHotKey(None,9003,0x4000,0x7C)
  user.UnregisterHotKey(None,9003)
  api.hotkey_manager.active=lambda:True
  time.sleep(.12)
  assert len(api.hotkey_manager.registered)==4
  report['nativeHotkeys']={'actions':actions[before:],'keyboardEvents':True,'noRepeat':True,
                          'conflictRollback':True,'pauseResume':True,'savedConfiguration':True,
                          'inactiveContextReleasesKeys':True}
  # Verify actual own-window capture only if this runner has foreground focus.
  hwnd=int(target['id']);api.native.user.SetForegroundWindow.argtypes=[wintypes.HWND]
  api.native.user.SetForegroundWindow(hwnd);time.sleep(.4)
  foreground=api.native.user.GetAncestor(api.native.user.GetForegroundWindow(),2)
  if foreground==hwnd:
   assert api._hotkey_active()
   selected=api.target;api.target=None;assert not api._hotkey_active();api.target=selected
   out=api.capture();assert out['width']>200 and out['height']>150 and out['image'].startswith('data:image/png;base64,')
   report['mssOwnWindowCapture']={'width':out['width'],'height':out['height']}
  else:report['mssOwnWindowCapture']={'skipped':'runner did not grant foreground focus'}
  report['scope']='Windows native GUI and synthetic own-window capture. No real game run.'
 except Exception:
  error.append(traceback.format_exc());report['error']=error[-1]
 finally:
  api.hotkey_manager.close();hotkey_folder.cleanup()
  dest=ROOT/'tests/windows-native-results.json';dest.write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8');print(json.dumps(report,ensure_ascii=False),flush=True)
  try:fixture.destroy()
  except Exception:pass
  try:app.destroy()
  except Exception:pass

webview.start(test,gui='edgechromium',private_mode=True,http_server=True)
if error:raise SystemExit(1)

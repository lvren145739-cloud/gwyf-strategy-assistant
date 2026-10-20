"""Real pywebview 6.2.1 injection + generated JS + Python RPC + actual UI.
The OS/game window list is a fixture; this does not run Windows WebView2.
Run with Playwright/Chromium and pywebview installed and web/ served at 8767.
"""
from pathlib import Path
import json,queue,re,sys,time
from importlib.metadata import version
from playwright.sync_api import sync_playwright
import webview,webview.util as util
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from app import API,DesktopBridge

METHODS={'status','windows','select_window','capture','open_image','recognize','load_state','save_state','compact','hotkeys'}
class NativeFixture:
    def __init__(self):
        self.fail=False
        self.rows=[{'id':'1234567890123','title':'Gamble With Your Friends','minimized':False},
                   {'id':'456','title':'记事本','minimized':False}]
    def windows(self):
        if self.fail:raise OSError('窗口枚举测试错误')
        return self.rows
class Controller(API):
    def __init__(self):
        super().__init__();self.native=NativeFixture();self.loads=0;self.saved=None
    def load_state(self):
        self.loads+=1;return None
    def save_state(self,data):
        self.saved=data;return True
    def compact(self,enabled):return True
    def capture(self):return {'fixture':True}
    def open_image(self):return None
    def recognize(self,regions,mode):return {'cards':[],'hiddenCount':0,'recognitionMs':0}

# Exercise the library's actual recursive scanner, not a hand-written API list.
controller=Controller();bridge=DesktopBridge(controller)
w=webview.create_window('bridge test','about:blank',js_api=bridge)
controller.window=w
w.js_api_endpoint=None
scripts=[];returns=queue.Queue()
w.run_js=lambda code:scripts.append(code)
w.evaluate_js=lambda code:returns.put(code)
start=time.perf_counter();util.inject_pywebview('edgechromium',w)
assert w.events._pywebviewready.wait(2),'Real pywebview API injection did not finish'
assert len(scripts)==2
injection_ms=round((time.perf_counter()-start)*1000,2)
funcs=json.loads(re.search(r"JSON.parse\('(.*)'\)",scripts[1]).group(1))
assert {r['func'] for r in funcs}==METHODS,funcs
assert not any('.' in r['func'] for r in funcs),'GUI/native methods leaked into RPC'

checks=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    def new_page():
        page=browser.new_page(viewport={'width':420,'height':820});errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        def post(source,payload):
            func,args,call_id=payload
            util.js_bridge_call(w,func,json.loads(args),call_id)
        page.expose_binding('_nativePost',post)
        page.add_init_script("window.chrome=window.chrome||{};window.chrome.webview={postMessage:payload=>window._nativePost(payload)};")
        return page,errors
    def pump(page,condition,timeout=8):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            while not returns.empty():page.evaluate(returns.get())
            if page.evaluate(condition):return
            page.wait_for_timeout(10)
        raise AssertionError('Timed out: '+condition+' / '+page.locator('#status').inner_text())
    def ready(page):
        pump(page,"nativeReady && nativeConnecting===null && document.querySelector('#target').value==='1234567890123'")
        assert page.locator('#nativeBadge').inner_text().startswith('桌面已连接')
        assert controller.target=='1234567890123'
    # UI runs before native API injection. An empty API must not be treated as ready.
    page,errors=new_page();page.goto('http://127.0.0.1:8769/desktop.html')
    page.evaluate(scripts[0]);page.wait_for_timeout(150)
    assert page.evaluate('typeof window.pywebview.api.windows')=='undefined'
    assert page.locator('#nativeBadge').inner_text()=='正在连接桌面…'
    page.evaluate(scripts[1]);ready(page);assert not errors,errors
    assert 'Gamble With Your Friends' in page.locator('#windowStatus').inner_text()
    checks.append('late bridge + initially empty API + real generated windows() RPC')
    # A repeated readiness event must not reload state/overwrite an edited hand.
    loaded=controller.loads
    page.evaluate("window.dispatchEvent(new Event('pywebviewready'));window.dispatchEvent(new Event('pywebviewready'))")
    page.wait_for_timeout(50);assert controller.loads==loaded
    checks.append('readiness is idempotent')
    # Refresh preserves a manually selected non-game window.
    page.locator('#target').select_option('456');pump(page,"document.querySelector('#windowStatus').textContent.includes('记事本')")
    page.locator('#refresh').click();pump(page,"document.querySelector('#target').value==='456'")
    assert controller.target=='456'
    checks.append('manual selection survives refresh; 64-bit HWND stays a string')
    # Minimized games stay visible, but clearly require restoration before capture.
    controller.native.rows[0]['minimized']=True
    page.locator('#target').select_option('');pump(page,"document.querySelector('#windowStatus').textContent==='请选择游戏窗口。'")
    page.locator('#refresh').click();ready(page)
    assert '最小化' in page.locator('#target option').nth(1).inner_text()
    assert '恢复' in page.locator('#windowStatus').inner_text()
    controller.native.rows[0]['minimized']=False
    checks.append('minimized game remains listed with restore hint')
    # Empty lists and native failures are distinct and retryable.
    original=controller.native.rows;controller.native.rows=[]
    page.locator('#refresh').click();pump(page,"document.querySelector('#windowStatus').textContent.includes('未找到')")
    assert controller.target is None
    controller.native.fail=True;page.locator('#refresh').click()
    pump(page,"document.querySelector('#windowStatus').textContent.includes('窗口枚举测试错误')")
    controller.native.fail=False;controller.native.rows=original;page.locator('#refresh').click();ready(page)
    assert not errors,errors
    checks.append('empty list, native exception, recovery')
    # Exercise the remaining JS->Python RPC wrappers, including JSON arguments.
    page.evaluate("() => {window.rpcDone=false;Promise.all([pywebview.api.capture(),pywebview.api.open_image(),pywebview.api.recognize({player:[0,0,1,1]},'blackjack'),pywebview.api.save_state({test:1}),pywebview.api.compact(true),pywebview.api.hotkeys({op:'get'})]).then(v=>{window.rpcValues=v;window.rpcDone=true});}")
    pump(page,'window.rpcDone===true');assert controller.saved=={'test':1}
    assert page.evaluate('rpcValues[0].fixture')
    checks.append('all ten exported RPC methods return through real Python bridge')
    # Drain the delayed status update before switching pages (one test Window).
    until=time.monotonic()+.8
    while time.monotonic()<until:
        while not returns.empty():page.evaluate(returns.get())
        page.wait_for_timeout(10)
    page.close()
    # Native ready event fires BEFORE ui.js: the existing API must still connect.
    page,errors=new_page()
    early_code=scripts[0]+'\n'+scripts[1]+'\n'+(root/'web/ui.js').read_text('utf-8')
    page.route('**/ui.js',lambda route:route.fulfill(status=200,content_type='application/javascript',body=early_code))
    page.goto('http://127.0.0.1:8769/desktop.html');ready(page);assert not errors,errors
    checks.append('bridge ready before UI and event listener')
    page.close()
    # Real native entry detects incomplete interfaces and offers retry.
    page,errors=new_page();page.goto('http://127.0.0.1:8769/desktop.html')
    page.evaluate(scripts[0]);page.evaluate(scripts[1].replace('"windows"','"missing_windows"'))
    pump(page,"document.querySelector('#nativeBadge').textContent==='桌面连接失败'",15)
    assert '超时' in page.locator('#windowStatus').inner_text()
    assert not page.locator('#refresh').is_disabled()
    page.evaluate('window.pywebview._createApi('+json.dumps(funcs)+')');page.locator('#refresh').click();ready(page);assert not errors,errors
    assert not page.locator('#status').evaluate('(e)=>e.classList.contains(\'error\')'),'Old error survived recovery'
    checks.append('missing method: visible timeout and retry recovery')
    page.screenshot(path=str(root/'tests/bridge-connected.png'),full_page=True)
    page.close()
    # Manual browser preview remains usable and does not claim a native connection.
    page,errors=new_page();page.goto('http://127.0.0.1:8769/')
    page.locator('#refresh').click()
    assert 'Start-Windows.bat' in page.locator('#status').inner_text()
    assert page.locator('#nativeBadge').inner_text()=='浏览器预览'
    assert not errors,errors;page.close();browser.close()
    checks.append('manual preview accurately explains native-only functions')
report={'framework':'pywebview '+version('pywebview'),'injectionMs':injection_ms,'checks':checks,
        'scope':'Actual framework scanner, JS generation, RPC dispatch and UI. Windows EnumWindows/WebView2/game capture not run.'}
(root/'tests/bridge-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf-8')
print(json.dumps(report,ensure_ascii=False))

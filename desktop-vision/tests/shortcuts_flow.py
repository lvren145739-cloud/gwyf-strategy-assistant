"""UI shortcut recording, persistence, conflicts and archive guards (mock OS)."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);page=b.new_page(viewport={'width':420,'height':820});errors=[];checks=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.add_init_script('''(() => {
  window.keyConfig=JSON.parse(localStorage.getItem('fixtureKeys')||'null')||{capture:'F8',archive:'F9',accept:'F10',reset:'F11'};
  window.keyPaused=false;window.keyCalls=[];
  const make=(rank,suit,role='player')=>({rank,suit,role,score:.999,suitScore:.999,cardScore:.999,review:false});
  window.fixture={autoReady:true,warnings:[],hiddenCount:1,recognitionMs:90,cards:[make('2','clubs'),make('3','hearts'),make('4','spades','dealer')]};
  window.pywebview={api:{status:async()=>({version:'0.3.1',modelBytes:11000000,hotkey:'F8 识牌 · F9 归档 · F10 采用'}),windows:async()=>[{id:'123',title:'Gamble With Your Friends'}],select_window:async()=>true,load_state:async()=>null,save_state:async()=>true,compact:async()=>true,open_image:async()=>null,
   capture:async()=>{const c=document.createElement('canvas');c.width=960;c.height=540;return {image:c.toDataURL(),width:960,height:540};},recognize:async()=>fixture,
   hotkeys:async req=>{keyCalls.push(req.op);if(req.op==='pause')keyPaused=true;if(req.op==='resume')keyPaused=false;if(req.op==='set'){if(req.config.capture==='F12')throw Error('F12 被占用；原快捷键保持生效。');keyConfig={...req.config};localStorage.setItem('fixtureKeys',JSON.stringify(keyConfig));}return {config:{...keyConfig},errors:{},paused:keyPaused,available:true};}
  }};
 })();''')
 def ready():page.wait_for_function('nativeReady && nativeConnecting===null')
 def record(action,key):
  page.locator('[data-record-shortcut="'+action+'"]').click();page.wait_for_function('recordingAction==='+json.dumps(action));page.keyboard.press(key);page.wait_for_function('recordingAction===null && !shortcutPending')
 page.goto('http://127.0.0.1:8769/desktop.html');ready();page.bring_to_front()
 assert page.locator('[data-shortcut-label=capture]').inner_text()=='F8'
 page.locator('#hotkeySettings').click();record('capture','F7');assert page.evaluate('keyPaused') is False
 assert page.locator('[data-shortcut-label=capture]').inner_text()=='F8'
 record('archive','Control+Alt+a');page.locator('#saveShortcuts').click();page.wait_for_function("shortcutConfig.capture==='F7' && shortcutConfig.archive==='Ctrl+Alt+A'")
 checks.append('single-key and modifier recording; native pause/resume; staged until save')
 page.reload();ready();assert page.locator('[data-shortcut-label=capture]').inner_text()=='F7';assert page.locator('[data-shortcut-label=archive]').inner_text()=='Ctrl+Alt+A'
 checks.append('saved shortcuts restored after page reload')
 page.locator('#hotkeySettings').click();page.locator('[data-record-shortcut=accept]').click();page.wait_for_function("recordingAction==='accept'");page.keyboard.press('F7');assert '重复' in page.locator('#shortcutStatus').inner_text();page.keyboard.press('Escape');page.wait_for_function('recordingAction===null && !shortcutPending');assert not page.evaluate('keyPaused')
 checks.append('duplicate blocked; Escape restores native keys')
 record('capture','F12');page.locator('#saveShortcuts').click();page.wait_for_function("document.querySelector('#shortcutStatus').textContent.includes('被占用')");assert page.evaluate('shortcutConfig.capture')=='F7'
 checks.append('OS conflict preserves previously active bindings')
 page.locator('#resetShortcuts').click();page.locator('#saveShortcuts').click();page.wait_for_function("shortcutConfig.capture==='F8'")
 page.locator('[data-record-shortcut=archive]').click();page.wait_for_function("recordingAction==='archive'");page.evaluate("dispatchEvent(new Event('blur'))");page.wait_for_function('recordingAction===null && !shortcutPending');assert not page.evaluate('keyPaused')
 checks.append('restore defaults and blur cancels recording')
 page.locator('[data-disable-shortcut=accept]').click();page.locator('#saveShortcuts').click();page.wait_for_function("shortcutConfig.accept===''");checks.append('individual shortcut can be disabled')
 page.evaluate('captureNow()');page.wait_for_function("document.querySelector('#advice h1').textContent.includes('HIT')")
 page.evaluate('busy=true;archiveCurrent();busy=false');assert page.locator('#usedCount').inner_text()=='0 张';checks.append('archive ignored while capture is busy')
 page.evaluate("fixture.autoReady=false;fixture.cards[2].rank=null;fixture.cards[2].review=true;captureNow()")
 page.wait_for_function("!document.querySelector('#draftPanel').hidden");page.evaluate('archiveCurrent()');assert page.locator('#usedCount').inner_text()=='0 张';assert '先核对' in page.locator('#status').inner_text()
 checks.append('uncertain draft cannot archive the previous hand')
 page.locator('#draft [data-field=rank]').nth(2).select_option('4');page.evaluate('acceptDraft()');page.wait_for_function("document.querySelector('#advice h1').textContent.includes('HIT')")
 page.evaluate('archiveCurrent();archiveCurrent()');assert page.locator('#usedCount').inner_text()=='3 张';assert page.evaluate('state.blackjack.player.length')==0
 page.locator('#undo').click();assert page.locator('#usedCount').inner_text()=='0 张';assert page.evaluate('state.blackjack.player.length')==2
 checks.append('archive callback counts once; undo restores hand and leaves shortcuts unchanged')
 record('reset','Control+F11');page.locator('#saveShortcuts').click();page.wait_for_function("shortcutConfig.reset==='Ctrl+F11'")
 page.evaluate('archiveCurrent()');assert page.locator('#usedCount').inner_text()=='3 张'
 page.evaluate('resetUsedCards();resetUsedCards()');assert page.locator('#usedCount').inner_text()=='0 张';assert page.evaluate('state.undo.label')=='重置牌堆'
 page.locator('#undo').click();assert page.locator('#usedCount').inner_text()=='3 张';assert page.evaluate('shortcutConfig.reset')=='Ctrl+F11'
 checks.append('custom reset shortcut; clear used cards; repeated reset preserves undo; undo preserves bindings')
 page.locator('#compact').click();page.set_viewport_size({'width':420,'height':341});assert page.locator('#status').bounding_box()['y']+page.locator('#status').bounding_box()['height']<=341;assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');page.screenshot(path=str(ROOT/'tests/shortcuts-compact.png'));checks.append('compact same-screen layout')
 assert not errors,errors
 report={'errors':errors,'checks':checks,'scope':'Real Chromium UI, simulated OS bridge. Actual Win32 registration and key delivery tested separately.'};(ROOT/'tests/shortcuts-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False));b.close()

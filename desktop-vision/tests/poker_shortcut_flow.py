"""Actual Chromium, solver worker and state transitions; no real game inputs."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':420,'height':820});errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:8770/index.html')
 page.wait_for_function("typeof swapRecommended==='function'")
 def seed(royal=False):
  page.evaluate("""royal=>{state=V.blank();state.mode='poker';state=V.commit(state,(royal?['10','J','Q','K','A']:['2','J','Q','K','A']).map((rank,i)=>({rank,suit:!royal&&i===0?'diamonds':'spades',role:'player'})));draft=[];$('#draftPanel').hidden=true;render();calculate();}""",royal)
  page.wait_for_function('worker===null && lastResult?.solutions?.length',timeout=60000)
 def press(key):page.keyboard.press(key)
 def snapshot():return page.evaluate('JSON.stringify(state)')
 seed(True);before=snapshot();press('F7');assert snapshot()==before
 seed();assert page.evaluate('lastResult.solutions[0].mask')==30
 old=page.evaluate('state.poker.player');discarded=page.evaluate('V.cardId(state.poker.player[0])')
 # A busy capture must not permit UI undo or shortcut state changes.
 before=snapshot();page.evaluate('busy=true');press('F7');page.locator('#undo').click();assert snapshot()==before;page.evaluate('busy=false')
 # A draft invalidates an in-flight/old advice, and cannot be exchanged.
 page.evaluate('draft=state.poker.player.map(c=>({...c,role:"player"}));renderDraft()')
 assert page.evaluate('worker===null && lastResult===null');press('F7');assert snapshot()==before
 page.locator('#cancelDraft').click();page.wait_for_function('worker===null && lastResult?.solutions?.length',timeout=60000)
 # An old mask cannot be applied to a changed order.
 page.evaluate('state.poker.player.reverse()');before=snapshot();press('F7');assert snapshot()==before
 page.wait_for_function('worker===null && lastResult?.solutions?.length',timeout=60000)
 assert page.evaluate('lastResult.solutions[0].mask')==15
 press('F7');assert page.evaluate('state.poker.used')==[discarded]
 assert page.evaluate("state.poker.phase==='replacement' && state.poker.player.filter(c=>!c).length===1")
 before=snapshot();press('F7');assert snapshot()==before
 # Undo restores the complete hand and discard count.
 page.locator('#undo').click();assert page.evaluate("state.poker.phase==='initial' && !state.poker.used.length")
 page.wait_for_function('worker===null && lastResult?.solutions?.length',timeout=60000)
 # Save a custom shortcut through actual recording controls.
 page.locator('#hotkeySettings').click();page.locator('[data-record-shortcut=discard]').click()
 page.wait_for_function("recordingAction==='discard'");press('Control+g');page.wait_for_function('!recordingAction && !shortcutPending')
 page.locator('#saveShortcuts').click();page.wait_for_function("shortcutConfig.discard==='Ctrl+G' && !shortcutPending")
 page.locator('#hotkeySettings').focus();before=snapshot();press('F7');assert snapshot()==before
 press('Control+g');assert page.evaluate("state.poker.phase==='replacement'")
 # Reject discarded cards, accept complete replacements, avoid double exchange.
 assert page.evaluate("""()=>{try{V.commit(state,[...state.poker.player.filter(Boolean),{rank:'2',suit:'diamonds'}].map(c=>({...c,role:'player'})));return false}catch(e){return e.message.includes('已用牌')}}""")
 page.evaluate("mutate(()=>V.commit(state,[...state.poker.player.filter(Boolean),{rank:'10',suit:'spades'}].map(c=>({...c,role:'player'}))))")
 assert page.locator('#advice h1').inner_text()=='补牌完成 · 等待结算'
 before=snapshot();press('Control+g');assert snapshot()==before
 page.evaluate('archiveCurrent()');assert page.evaluate('state.poker.used.length')==6
 page.locator('#undo').click();assert page.evaluate("state.poker.used.length===1 && state.poker.phase==='replacement'")
 # Reload preserves independent shortcut configuration and hand phase.
 page.reload();page.wait_for_function("shortcutConfig.discard==='Ctrl+G'")
 assert page.evaluate("state.poker.phase==='replacement' && state.poker.used.length===1")
 seed();page.locator('#compact').click();page.set_viewport_size({'width':420,'height':341})
 page.evaluate('window.scrollTo(0,0)')
 assert page.locator('#discard').bounding_box()['y']+page.locator('#discard').bounding_box()['height']<=341
 for width in [360,420,560]:
  page.set_viewport_size({'width':width,'height':341});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 assert not errors,errors
 result={'checks':['real solver keep-all no-op','F7 applies current recommendation','busy capture blocks mutation','draft invalidates old advice','stale ordered-hand mask rejected','discarded cards immediately recorded','no repeated exchange','undo restores hand/history','custom Ctrl+G recording/save/reload','old key inactive after customization','discarded card rejected in replacement','replacement complete no second exchange','archive includes discarded plus final cards','archive undo','compact same-screen and no horizontal scrolling'], 'errors':errors,'scope':'Actual Chromium UI and solver workers; native OS registration tested separately on Windows; no game inputs.'}
 (ROOT/'tests/poker-shortcut-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
 print(json.dumps(result,ensure_ascii=False));browser.close()

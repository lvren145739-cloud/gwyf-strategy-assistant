"""Actual UI/solver with fixture native capture; model tested separately."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);page=browser.new_page(viewport={'width':420,'height':820});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.add_init_script('''(() => {
  const make=(rank,suit,role='player')=>({rank,suit,role,score:.999,suitScore:.999,cardScore:.999,review:false});
  window.makeCard=make;
  window.fixture={autoReady:true,warnings:[],rejectedCount:7,hiddenCount:1,recognitionMs:150,cards:[make('9','clubs'),make('8','clubs'),make('A','hearts','dealer'),{role:'dealer',faceDown:true,review:false}]};
  window.recognitionCalls=[];window.saved=[];
  window.pywebview={api:{status:async()=>({version:'0.3.0',modelBytes:7000000,hotkey:'Ctrl+Shift+Space',python:'3.14.8'}),windows:async()=>[{id:'123',title:'Gamble With Your Friends'}],select_window:async()=>true,load_state:async()=>null,save_state:async data=>{saved.push(data);return true;},capture:async()=>{const c=document.createElement('canvas');c.width=960;c.height=540;return {image:c.toDataURL(),width:960,height:540,digest:'frame'};},recognize:async(regions,mode)=>{recognitionCalls.push({regions,mode});return fixture;},compact:async()=>true,open_image:async()=>null}};
 })();''')
 page.goto('http://127.0.0.1:8768/desktop.html');page.wait_for_function('nativeReady && nativeConnecting===null')
 page.evaluate('captureNow()');page.wait_for_function("document.querySelector('#advice h1').textContent.includes('HIT')",timeout=15000)
 assert page.locator('#draftPanel').is_hidden()
 assert '已自动识别并计算' in page.locator('#status').inner_text()
 assert page.evaluate('recognitionCalls[0].regions')=={}
 assert page.evaluate('state.blackjack.player.map(c=>c.rank)')==['9','8']
 assert page.evaluate('state.blackjack.dealer[0].rank')=='A'
 assert page.locator('#usedCount').inner_text()=='0 张'
 undo=page.evaluate('JSON.stringify(state.undo)')
 page.evaluate('captureNow()');page.wait_for_function("document.querySelector('#advice h1').textContent.includes('HIT')")
 assert page.evaluate('JSON.stringify(state.undo)')==undo
 assert page.locator('#usedCount').inner_text()=='0 张'
 # Refuse an incomplete/uncertain result and stop displaying old advice.
 page.evaluate("fixture.cards[0].rank=null;fixture.cards[0].score=1;fixture.cards[0].review=true;fixture.autoReady=false")
 page.evaluate('captureNow()');assert not page.locator('#draftPanel').is_hidden()
 assert page.locator('#advice h1').inner_text()=='本次识别需要核对'
 assert page.locator('#draft .score').first.inner_text()=='未读全'
 assert page.evaluate('state.blackjack.player.map(c=>c.rank)')==['9','8']
 assert page.locator('#usedCount').inner_text()=='0 张'
 page.evaluate("fixture.cards=[makeCard('9','clubs'),makeCard('9','clubs'),makeCard('A','hearts','dealer')];fixture.autoReady=true")
 page.evaluate('captureNow()');assert '重复' in page.locator('#advice p').inner_text()
 # The reliable five-card poker hand calculates without clicking adoption.
 page.locator('[data-mode=poker]').click()
 page.evaluate("fixture.cards=['10','J','Q','K','A'].map(r=>makeCard(r,'spades'));fixture.hiddenCount=0")
 page.evaluate('captureNow()');page.wait_for_function("document.querySelector('#advice h1').textContent==='保留全部五张'",timeout=20000)
 assert page.locator('#draftPanel').is_hidden();assert page.locator('#usedCount').inner_text()=='0 张'
 page.evaluate('fixture.cards.pop()');page.evaluate('captureNow()')
 assert not page.locator('#draftPanel').is_hidden();assert '完整五张' in page.locator('#advice p').inner_text()
 # Return to automatic blackjack, then archive still explicitly records known cards.
 page.locator('[data-mode=blackjack]').click()
 page.evaluate("fixture.cards=[makeCard('9','clubs'),makeCard('8','clubs'),makeCard('A','hearts','dealer')];fixture.autoReady=true")
 page.evaluate('captureNow()');page.wait_for_function("document.querySelector('#advice h1').textContent.includes('HIT')")
 page.locator('#archive').click();assert page.locator('#usedCount').inner_text()=='3 张'
 page.locator('#undo').click();assert page.locator('#usedCount').inner_text()=='0 张'
 for width in [360,420,560]:
  page.set_viewport_size({'width':width,'height':820});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 page.set_viewport_size({'width':420,'height':341});page.locator('#compact').click()
 assert page.locator('#status').bounding_box()['y']+page.locator('#status').bounding_box()['height']<=341
 assert not errors,errors
 page.screenshot(path=str(root/'tests/automatic-compact.png'))
 print(json.dumps({'errors':errors,'checks':['no ROI required','17 vs A automatic HIT','repeat preserves undo/history','uncertain stops old advice','missing rank never shows 100%','duplicate blocks automatic adoption','royal flush automatic hold','incomplete poker blocks','explicit archive/undo','compact same-screen']},ensure_ascii=False));browser.close()

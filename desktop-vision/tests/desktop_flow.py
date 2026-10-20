"""Browser exercises the real UI through a simulated native capture bridge.
Native OS capture itself is intentionally not claimed as tested here.
"""
from playwright.sync_api import sync_playwright
from pathlib import Path
import json
root=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 page=b.new_page(viewport={'width':560,'height':820});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:8768/')
 page.evaluate('''() => {
   localStorage.clear(); state=VisionState.blank();
   state.regions.blackjack={player:[.3,.5,.7,.7],dealer:[.3,.3,.7,.4]};
   const make=(rank,role,suit='spades',score=1)=>({rank,role,suit,score,suitScore:score,review:score<.9});
   window.fixture=[make('5','player','hearts'),make('2','player','hearts'),make('9','dealer','clubs'),{...make(null,'dealer'),faceDown:true}];
   const canvas=document.createElement('canvas');canvas.width=960;canvas.height=540;canvas.getContext('2d').fillRect(0,0,960,540);
   window.pywebview={api:{capture:async()=>({image:canvas.toDataURL(),width:960,height:540,digest:'one-frame'}),recognize:async()=>({cards:fixture,hiddenCount:1,recognitionMs:5}),save_state:async()=>true,compact:async()=>true}};
 }''')
 for _ in range(3):
  page.evaluate('captureNow()');page.wait_for_function("!document.querySelector('#draftPanel').hidden")
  assert page.locator('#draft .draft-card').count()==3
  assert '核对' in page.locator('#advice h1').inner_text()
  page.evaluate('acceptDraft()');page.wait_for_function("document.querySelector('#advice h1').textContent.includes('HIT')")
  assert page.locator('#usedCount').inner_text()=='0 张'
 page.evaluate("fixture.push({rank:'7',role:'dealer',suit:'spades',score:1,suitScore:1})")
 page.evaluate('captureNow()');page.wait_for_function("!document.querySelector('#draftPanel').hidden");page.evaluate('acceptDraft()')
 assert '庄家阶段' in page.locator('#advice h1').inner_text()
 page.locator('#archive').click();assert page.locator('#usedCount').inner_text()=='4 张'
 page.locator('#undo').click();assert page.locator('#usedCount').inner_text()=='0 张'
 # The same native bridge may fail; old advice must not survive as a fresh result.
 page.evaluate("() => {pywebview.api.recognize=async()=>{throw Error('模型测试错误')};}")
 page.locator('#read').click();page.wait_for_function("document.querySelector('#advice h1').textContent==='识别未完成'")
 assert '模型测试错误' in page.locator('#status').inner_text()
 # Simulate a five-card draft and verify the adoption button is immediately accessible.
 page.evaluate('''() => {state.mode='poker';draft=['10','J','Q','K','A'].map(rank=>({rank,role:'player',suit:'spades',score:1,suitScore:1}));render();renderDraft();}''')
 page.evaluate('scrollTo(0,0)')
 for width in [360,420,560]:
  page.set_viewport_size({'width':width,'height':820});box=page.locator('#applyTop').bounding_box();assert box['y']+box['height']<820
 page.screenshot(path=str(root/'tests/preview-draft.png'),full_page=True)
 print(json.dumps({'errors':errors,'checks':['capture draft','exclude hidden back','repeat does not count','global confirm handler','dealer additions','archive and undo','recognition error clears advice','same-screen adoption']},ensure_ascii=False));assert not errors
 b.close()

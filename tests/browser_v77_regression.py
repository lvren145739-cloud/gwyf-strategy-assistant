import asyncio,json,threading
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1];KEY='GWYF_COMPANION_V7'
class H(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
async def main():
 server=ThreadingHTTPServer(('127.0.0.1',8781),partial(H,directory=str(ROOT)));threading.Thread(target=server.serve_forever,daemon=True).start()
 errors=[];external=[];checks=[]
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=await browser.new_page(viewport={'width':390,'height':844})
  page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:external.append(r.url) if not r.url.startswith(('http://127.0.0.1:8781','blob:','data:')) else None)
  await page.goto('http://127.0.0.1:8781/index.html#bj');await page.wait_for_timeout(130)
  async def nav(id):
   await page.locator(f'#quickNav [data-go="{id}"]').click();await page.wait_for_timeout(80)
   if id=='poker' and await page.locator('[data-action="pokerEntryClose"]').count():
    await page.locator('[data-action="pokerEntryClose"]').click();await page.wait_for_timeout(80)
  async def choose(path,value):await page.locator(f'button[data-path="{path}"][data-value="{value}"]').click();await page.wait_for_timeout(50)
  async def compare():
   await page.wait_for_timeout(130)
   if await page.locator('.bj-selection').count():
    await page.wait_for_function("!document.querySelector('#resultRegion .decision')?.textContent.includes('正在比较')",timeout=20000)
   assert await page.locator('.inline-decision-title').inner_text()==await page.locator('#resultRegion .hero-result .decision').first.inner_text()
  async def snap():return await page.evaluate(f'JSON.parse(localStorage.getItem("{KEY}")).state')
  def ok(s):checks.append(s);print('PASS',s,flush=True)
  assert await page.locator('#quickNav').evaluate('n=>getComputedStyle(n).position')=='static'
  await page.evaluate('scrollTo(0,650)');await page.wait_for_timeout(50)
  assert await page.locator('#quickNav').evaluate('n=>n.getBoundingClientRect().bottom')<0
  ok('category navigation scrolls off the screen instead of covering game controls')
  for width,height in [(320,740),(360,780),(390,844),(430,844)]:
   await page.set_viewport_size({'width':width,'height':height});await page.wait_for_timeout(80)
   await page.locator('.workspace>.stack>.panel').first.evaluate('n=>n.scrollIntoView({block:"start"})');await page.wait_for_timeout(90)
   geometry=await page.evaluate('''()=>{const s=document.querySelector('.bj-selection').getBoundingClientRect(),r=document.querySelector('.inline-decision').getBoundingClientRect();return {top:s.top,bottom:r.bottom,h:innerHeight,span:r.bottom-s.top}}''')
   assert geometry['top']>=60 and geometry['bottom']<=height,(width,geometry)
   await compare()
  ok('complete Blackjack selection and current recommendation fit together at 320/360/390/430px')
  await page.set_viewport_size({'width':390,'height':844});await page.wait_for_timeout(70)
  await nav('bj');assert await page.locator('.inline-decision').evaluate('n=>n.getBoundingClientRect().bottom')<=844
  await choose('bj.hard',19);await choose('bj.dealer','10');await compare();assert '停牌' in await page.locator('.inline-decision-title').inner_text()
  await choose('bj.type','soft');await choose('bj.soft',7);await choose('bj.dealer','6');await compare();assert '加倍' in await page.locator('.inline-decision-title').inner_text()
  await page.locator('[data-action="bjPhase"][data-value="later"]').click();await page.wait_for_timeout(60);await compare();assert '停牌' in await page.locator('.inline-decision-title').inner_text()
  await choose('bj.type','hard');await choose('bj.hard',19);await choose('bj.dealer','10')
  await page.locator('.workspace>.stack>.panel').first.evaluate('n=>n.scrollIntoView({block:"start"})');await page.evaluate('document.activeElement?.blur()');await page.wait_for_timeout(70)
  await page.screenshot(path=str(ROOT/'v77-blackjack-quick.png'))
  ok('Blackjack recommendation updates immediately for hand, dealer and hand-stage changes')
  anchors={'baccarat':'.bacc-table','money':'.color-choice','fortune':'.wheel-visual','hilo':'input[type="range"]','crash':'input[data-path="crash.target"]','dragon':'.ladder-track','penguin':'.ladder-track','mines':'[data-action="mineSafe"]','keno':'button[data-path="keno.picks"]','plinko':'.ladder-track','poker':'.poker-hand','craps':'[data-action="dice"]'}
  for id,selector in anchors.items():
   await nav(id);await compare();assert await page.locator('.inline-decision').is_visible()
   await page.locator('.workspace>.stack>.panel').first.evaluate('n=>n.scrollIntoView({block:"start"})');await page.wait_for_timeout(60)
   g=await page.evaluate('''selector=>{const q=document.querySelector('#content '+selector).getBoundingClientRect(),r=document.querySelector('.inline-decision').getBoundingClientRect();return {top:q.top,bottom:Math.max(q.bottom,r.bottom),height:innerHeight}}''',selector)
   assert g['top']>=60 and g['bottom']<=844,(id,g)
  ok('core controls and nearby result fit together for 12 other games at 390px')
  await nav('hilo');await choose('hilo.side','over');slider=page.locator('input[type="range"]')
  await slider.evaluate('n=>{n.value=25;n.dispatchEvent(new Event("input",{bubbles:true}))}');await page.wait_for_timeout(30);await compare()
  assert '75%' in await page.locator('.inline-decision-title').inner_text()
  await nav('mines');await page.locator('[data-action="mineSafe"]').click();await page.wait_for_timeout(50);await compare()
  await page.locator('.workspace>.stack>.panel').first.evaluate('n=>n.scrollIntoView({block:"start"})');await page.evaluate('document.activeElement?.blur()');await page.wait_for_timeout(70)
  await page.screenshot(path=str(ROOT/'v77-mines.png'))
  await nav('slots');await choose('slots.view','board');await compare()
  await page.locator('.workspace>.stack>.panel').first.evaluate('n=>n.scrollIntoView({block:"start"})');await page.wait_for_timeout(50)
  assert await page.locator('.inline-decision').evaluate('n=>n.getBoundingClientRect().bottom')<=844
  await page.locator('[data-action="slotFill"]').click();await page.wait_for_timeout(50);await compare();assert '175.000' in await page.locator('.inline-decision-title').inner_text()
  await nav('poker');await page.locator('[data-action="solvePoker"]').click()
  await page.wait_for_function("document.querySelector('#resultRegion')?.textContent.includes('推荐方案的最终牌型分布')",timeout=30000);await compare()
  ok('slider drag, Mines actions, Slots board and asynchronous Poker solve keep the nearby result current')
  ids=['recommend','roulette','baccarat','poker','bj','craps','money','fortune','hilo','crash','dragon','penguin','mines','keno','duck','plinko','slots','items','camera','budget','floors','sources']
  for width in [320,390,768,1440]:
   await page.set_viewport_size({'width':width,'height':900});await page.wait_for_timeout(100)
   for id in ids:
    await nav(id);assert not await page.evaluate('document.documentElement.scrollWidth>innerWidth'),(width,id)
    text=await page.locator('#content').inner_text();assert 'NaN' not in text and 'undefined' not in text
  assert not errors,errors;assert not external,external
  ok('22 pages fit four widths; no JavaScript errors or external requests')
  (ROOT/'tests/v77-regression-results.json').write_text(json.dumps({'checks':checks,'errors':errors,'externalRequests':external},ensure_ascii=False,indent=2))
  await browser.close()
 server.shutdown()
asyncio.run(main())

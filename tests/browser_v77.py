import asyncio,json,threading
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1];KEY='GWYF_COMPANION_V7'
class H(SimpleHTTPRequestHandler):
 def log_message(self,*a):pass
async def main():
 server=ThreadingHTTPServer(('127.0.0.1',8780),partial(H,directory=str(ROOT)));threading.Thread(target=server.serve_forever,daemon=True).start()
 checks=[];errors=[]
 async with async_playwright() as p:
  b=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);q=await b.new_page(viewport={'width':390,'height':844});q.on('pageerror',lambda e:errors.append(str(e)))
  async def click(a,v=None):await q.locator(f'[data-action="{a}"]'+(f'[data-value="{v}"]' if v is not None else '')).click();await q.wait_for_timeout(100)
  async def snap():return await q.evaluate(f'JSON.parse(localStorage.getItem("{KEY}")).state')
  async def choose(p,v):await q.locator(f'button[data-path="{p}"][data-value="{v}"]').click();await q.wait_for_timeout(140)
  async def solve():
   await click('solvePoker');await q.wait_for_function("document.querySelector('#resultRegion')?.textContent.includes('推荐方案的最终牌型分布')",timeout=30000)
  def ok(s):checks.append(s);print('PASS',s,flush=True)
  await q.goto('http://127.0.0.1:8780/index.html#poker');await click('pokerEntryClear')
  hand=[12,0,14,28,43]
  for c in hand:await click('pokerEntryCard',c)
  await click('pickCard',1);await click('pokerEntryCard',1)
  a=(await snap())['poker'];assert a['used']==[0];assert a['cards'][1]==1
  await click('pokerEntryUndo');a=(await snap())['poker'];assert a['used']==[] and a['cards']==hand
  await click('pokerEntryCard',1);await q.reload();await q.wait_for_timeout(100)
  assert (await snap())['poker']['used']==[0]
  await click('pokerNext');assert set((await snap())['poker']['used'])=={0,12,1,14,28,43}
  ok('single-card replacement immediately excludes old card; undo restores hand AND history; reload and archive keep both generations')
  await q.locator('[data-path="poker.track"]').check();await q.wait_for_timeout(100);await click('pokerClearUsed');await click('pokerEntryClear')
  for c in hand:await click('pokerEntryCard',c)
  await solve();kept=await q.locator('.poker-hand .poker-card').evaluate_all('ns=>ns.map((n,i)=>n.classList.contains("held")?i:null).filter(x=>x!==null)')
  discarded=[c for i,c in enumerate(hand) if i not in kept]
  await click('pokerExchange');a=(await snap())['poker'];assert set(a['used'])==set(discarded)
  assert [i for i,c in enumerate(a['cards']) if c is not None]==kept
  for c in discarded:assert await q.locator(f'[data-action="pokerEntryCard"][data-value="{c}"]').is_disabled()
  choices=[c for c in range(52) if c not in hand]
  for c in choices[:len(discarded)]:await click('pokerEntryCard',c)
  a=(await snap())['poker'];assert None not in a['cards'];assert set(a['used'])==set(discarded)
  current=a['cards'];await click('pokerNext');assert set((await snap())['poker']['used'])==set(discarded+current)
  ok('recommended batch exchange archives every discard before replacements, preserves held cards, skips held slots and archives final hand without loss')
  await q.locator('#quickNav [data-go="bj"]').click();await q.wait_for_timeout(200);await choose('bj.mode','cards')
  await q.wait_for_function("!document.querySelector('#resultRegion .decision').textContent.includes('正在比较')",timeout=15000)
  assert 'HIT' in await q.locator('.inline-decision-title').inner_text()
  # All player/dealer controls and the result should fit on each phone.
  for width,height in [(320,740),(360,780),(390,844),(430,844)]:
   await q.set_viewport_size({'width':width,'height':height});await q.locator('.workspace>.stack>.panel').first.evaluate('n=>n.scrollIntoView({block:"start"})');await q.wait_for_timeout(300)
   g=await q.evaluate('''()=>{const s=document.querySelector('.bj-selection').getBoundingClientRect(),d=document.querySelector('.inline-decision').getBoundingClientRect(),a=document.querySelector('[data-action="bjArchive"]').getBoundingClientRect();return {top:s.top,result:d.bottom,archive:a.bottom,h:innerHeight}}''')
   assert g['top']>=60 and g['result']<=height,(width,g)
   assert g['archive']<=height,(width,g)
  await q.set_viewport_size({'width':390,'height':844});await q.wait_for_timeout(300)
  await q.locator('.workspace>.stack>.panel').first.evaluate('n=>n.scrollIntoView({block:"start"})');await q.wait_for_timeout(100);await q.evaluate("document.getElementById('toast').classList.remove('show')");await q.screenshot(path=str(ROOT/'v77-blackjack-selection.png'))
  await click('bjDealerAdd','6');assert '庄家阶段' in await q.locator('.inline-decision-title').inner_text()
  await click('bjDealerAdd','A');assert await q.locator('[data-action="bjDealerAdd"][data-value="2"]').is_disabled()
  await q.locator('.workspace>.stack>.panel').first.evaluate('n=>n.scrollIntoView({block:"start"})');await q.evaluate('document.activeElement?.blur()');await q.wait_for_timeout(150);await q.screenshot(path=str(ROOT/'v77-blackjack-archive.png'))
  await q.reload();await q.wait_for_timeout(150);assert (await snap())['bj']['dealerCards']==['6','A']
  await click('bjArchive');a=(await snap())['bj'];expected=[1,0,0,0,0,2,0,0,0,2]
  assert a['used']==expected,a;assert a['cards']==[] and a['dealer']=='' and a['dealerCards']==[]
  assert await q.locator('[data-action="bjArchive"]').is_disabled()
  assert '等待手牌' in await q.locator('.inline-decision-title').inner_text()
  await click('bjArchiveUndo');a=(await snap())['bj'];assert a['used']==[0]*10 and a['cards']==['10','6'] and a['dealerCards']==['6','A']
  await click('bjArchive');await click('bjAdd','8');await click('bjAdd','9');await choose('bj.dealer','5')
  await q.wait_for_function("!document.querySelector('#resultRegion .decision').textContent.includes('正在比较')",timeout=15000)
  assert (await snap())['bj']['used']==expected
  assert '已用 5 张' in await q.locator('#resultRegion').inner_text()
  ok('Blackjack dealer hole/draws persist, S17 stops dealer input; archive records both hands exactly once, resets upcard, supports undo and applies to next recommendation')
  ok('Blackjack player/dealer controls, recommendation and archive fit together at 320/360/390/430px')
  # Bust remains archivable; unknown hole never guessed. Invalid multi-copy hand blocked.
  await click('bjAdd','K');assert '爆牌' in await q.locator('.inline-decision-title').inner_text();await click('bjArchive')
  a=(await snap())['bj'];assert a['used'][7]==1 and a['used'][8]==1 and a['used'][4]==1 and a['used'][9]==3
  await q.locator('[data-path="bj.track"]').check();await q.wait_for_timeout(100);await click('bjClearUsed');await choose('bj.dealer','10')
  for _ in range(5):await click('bjAdd','2')
  assert await q.locator('[data-action="bjArchive"]').is_disabled()
  ok('bust hand can archive all known cards, unknown hole is not guessed, impossible rank count blocks archive')
  for width in [320,390,768,1440]:
   await q.set_viewport_size({'width':width,'height':900});await q.wait_for_timeout(250)
   for tab in ['poker','bj','roulette','slots']:
    await q.locator(f'#quickNav [data-go="{tab}"]').click();await q.wait_for_timeout(100)
    assert not await q.evaluate('document.documentElement.scrollWidth>innerWidth'),(width,tab)
  assert not errors,errors
  (ROOT/'tests/v77-results.json').write_text(json.dumps({'checks':checks,'errors':errors},ensure_ascii=False,indent=2))
  await b.close()
 server.shutdown()
asyncio.run(main())
